from django.conf import settings


def site(request):
    return {
        'site_title': settings.SITE_TITLE,
        'site_tagline': settings.SITE_TAGLINE,
        'login_providers': [
            (provider, provider.title())
            for provider, configured in settings.NOISE_AUTH_PROVIDER_MAP.items()
            if configured or (provider == 'phone' and settings.NOISE_AUTH_PHONE_ENABLED)
        ],
    }
