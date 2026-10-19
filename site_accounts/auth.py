import base64
import hashlib
import json
import secrets
from urllib.parse import urlencode

import jwt
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify

from .models import UserIdentity


AUTH_SESSION_KEY = "noise_auth_request"


class NoiseAuthError(Exception):
    pass


def auth_is_configured():
    return all((
        settings.NOISE_AUTH_COGNITO_DOMAIN,
        settings.NOISE_AUTH_COGNITO_CLIENT_ID,
        settings.NOISE_AUTH_COGNITO_USER_POOL_ID,
    ))


def hosted_ui_url(path):
    domain = settings.NOISE_AUTH_COGNITO_DOMAIN.rstrip("/")
    if not domain.startswith(("http://", "https://")):
        domain = f"https://{domain}"
    return f"{domain}/{path.lstrip('/')}"


def begin_auth(request, provider, next_path):
    if not auth_is_configured():
        raise NoiseAuthError("Noise login is not configured yet.")

    if provider not in settings.NOISE_AUTH_PROVIDER_MAP:
        raise NoiseAuthError("Unknown login provider.")
    provider_name = settings.NOISE_AUTH_PROVIDER_MAP.get(provider)
    if provider == "phone" and not settings.NOISE_AUTH_PHONE_ENABLED:
        raise NoiseAuthError("Phone login is not configured yet.")
    if provider != "phone" and not provider_name:
        raise NoiseAuthError(f"{provider.title()} login is not configured yet.")

    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    request.session[AUTH_SESSION_KEY] = {
        "state": state,
        "verifier": verifier,
        "next": next_path,
    }

    params = {
        "client_id": settings.NOISE_AUTH_COGNITO_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile" if provider != "phone" else "openid phone profile",
        "redirect_uri": settings.NOISE_AUTH_REDIRECT_URI,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }
    if provider_name:
        params["identity_provider"] = provider_name
    return f"{hosted_ui_url('oauth2/authorize')}?{urlencode(params)}"


def complete_auth(request, code, state):
    auth_request = request.session.pop(AUTH_SESSION_KEY, None) or {}
    if not state or not secrets.compare_digest(state, auth_request.get("state", "")):
        raise NoiseAuthError("The login request expired or could not be verified.")

    try:
        response = requests.post(
            hosted_ui_url("oauth2/token"),
            data={
                "grant_type": "authorization_code",
                "client_id": settings.NOISE_AUTH_COGNITO_CLIENT_ID,
                "code": code,
                "redirect_uri": settings.NOISE_AUTH_REDIRECT_URI,
                "code_verifier": auth_request.get("verifier", ""),
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        raise NoiseAuthError("Cognito could not be reached.") from exc
    if not response.ok:
        raise NoiseAuthError("Cognito did not accept the login response.")

    id_token = response.json().get("id_token")
    if not id_token:
        raise NoiseAuthError("Cognito did not return an identity token.")

    issuer = (
        f"https://cognito-idp.{settings.NOISE_AUTH_COGNITO_REGION}.amazonaws.com/"
        f"{settings.NOISE_AUTH_COGNITO_USER_POOL_ID}"
    )
    try:
        signing_key = jwt.PyJWKClient(
            f"{issuer}/.well-known/jwks.json"
        ).get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.NOISE_AUTH_COGNITO_CLIENT_ID,
            issuer=issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise NoiseAuthError("The Cognito identity token could not be verified.") from exc
    return resolve_user(claims), auth_request.get("next") or "/noise/"


@transaction.atomic
def resolve_user(claims):
    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise NoiseAuthError("The identity token did not contain a subject.")

    existing = UserIdentity.objects.select_related("user").filter(
        kind=UserIdentity.COGNITO,
        identifier=subject,
    ).first()
    if existing:
        _assign_noise_groups(existing.user)
        return existing.user

    email = UserIdentity.normalize_identifier(UserIdentity.EMAIL, claims.get("email"))
    phone = UserIdentity.normalize_identifier(UserIdentity.PHONE, claims.get("phone_number"))
    email_verified = claims.get("email_verified") is True
    phone_verified = claims.get("phone_number_verified") is True

    user = None
    if email and email_verified:
        identity = UserIdentity.objects.select_related("user").filter(
            kind=UserIdentity.EMAIL,
            identifier=email,
            is_verified=True,
        ).first()
        user = identity.user if identity else None
    if user is None and phone and phone_verified:
        identity = UserIdentity.objects.select_related("user").filter(
            kind=UserIdentity.PHONE,
            identifier=phone,
            is_verified=True,
        ).first()
        user = identity.user if identity else None

    user_model = get_user_model()
    if user is None and email and email_verified:
        user = user_model.objects.filter(email__iexact=email).first()
    if user is None:
        username_base = slugify(email.split("@", 1)[0] if email else f"noise-{subject[:12]}") or "noise-user"
        username = username_base[:140]
        suffix = 1
        while user_model.objects.filter(username=username).exists():
            suffix += 1
            username = f"{username_base[:130]}-{suffix}"
        user = user_model(username=username, email=email if email_verified else "")
        user.set_unusable_password()
        user.save()

    UserIdentity.objects.create(
        user=user,
        kind=UserIdentity.COGNITO,
        identifier=subject,
        is_verified=True,
    )
    if email and email_verified:
        UserIdentity.objects.get_or_create(
            kind=UserIdentity.EMAIL,
            identifier=email,
            defaults={"user": user, "is_verified": True},
        )
        if not user.email:
            user.email = email
            user.save(update_fields=("email",))
    if phone and phone_verified:
        UserIdentity.objects.get_or_create(
            kind=UserIdentity.PHONE,
            identifier=phone,
            defaults={"user": user, "is_verified": True},
        )
    _store_federated_identity(user, claims.get("identities"))
    _assign_noise_groups(user)
    return user


def _store_federated_identity(user, raw_identities):
    if not raw_identities:
        return
    try:
        identities = json.loads(raw_identities) if isinstance(raw_identities, str) else raw_identities
    except (TypeError, ValueError):
        return
    kind_map = {
        "google": UserIdentity.GOOGLE,
        "facebook": UserIdentity.FACEBOOK,
        "instagram": UserIdentity.INSTAGRAM,
    }
    for identity in identities or []:
        kind = kind_map.get(str(identity.get("providerName") or "").casefold())
        identifier = str(identity.get("userId") or "").strip()
        if kind and identifier:
            UserIdentity.objects.get_or_create(
                kind=kind,
                identifier=identifier,
                defaults={"user": user, "is_verified": True},
            )


def _assign_noise_groups(user):
    from noise.models import Noise

    Noise.assign_default_groups_for_user(user)
