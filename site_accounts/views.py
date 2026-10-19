from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
from urllib.parse import urlencode

from .auth import NoiseAuthError, begin_auth, complete_auth, hosted_ui_url


def _safe_next(request):
    next_path = (request.GET.get("next") or "/noise/").strip()
    allowed_hosts = {
        request.get_host(),
    }
    if url_has_allowed_host_and_scheme(
        next_path,
        allowed_hosts=allowed_hosts,
        require_https=not settings.DEBUG,
    ):
        return next_path
    return "/noise/"


@require_GET
def noise_login(request, provider):
    try:
        return redirect(begin_auth(request, provider.casefold(), _safe_next(request)))
    except NoiseAuthError as exc:
        messages.error(request, str(exc))
        return redirect("/noise/")


@require_GET
def noise_auth_callback(request):
    if request.GET.get("error"):
        messages.error(request, "Login was cancelled or could not be completed.")
        return redirect("/noise/")
    try:
        user, next_path = complete_auth(
            request,
            request.GET.get("code", ""),
            request.GET.get("state", ""),
        )
    except (NoiseAuthError, ValueError) as exc:
        messages.error(request, str(exc))
        return redirect("/noise/")
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return redirect(next_path)


@require_POST
def noise_logout(request):
    logout(request)
    if not settings.NOISE_AUTH_COGNITO_DOMAIN:
        return redirect("/noise/")
    params = urlencode({
        "client_id": settings.NOISE_AUTH_COGNITO_CLIENT_ID,
        "logout_uri": settings.NOISE_AUTH_LOGOUT_URI,
    })
    return redirect(f"{hosted_ui_url('logout')}?{params}")
