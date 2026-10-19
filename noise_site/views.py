from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.http import require_safe
from noise.models import Noise


@require_safe
def media(request, filename):
    if not Noise.visible_queryset_for_user(request.user).filter(media=filename).exists():
        raise Http404
    media_root = Path(settings.MEDIA_ROOT).resolve()
    media_path = (media_root / filename).resolve()
    if not media_path.is_relative_to(media_root):
        raise Http404
    try:
        response = FileResponse(media_path.open('rb'), as_attachment=True)
    except (OSError, ValueError):
        raise Http404
    response['Content-Disposition'] = 'inline'
    if response['Content-Type'] not in {'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'video/mp4', 'video/webm'}:
        response['Content-Disposition'] = 'attachment'
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; sandbox"
    return response
