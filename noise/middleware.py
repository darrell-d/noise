import logging
from ipaddress import ip_address

from .models import Noise, NoiseVisit


logger = logging.getLogger(__name__)


class NoiseVisitTrackingMiddleware:
    TRACKED_URL_NAMES = {
        'index',
        'noise-add',
        'noise-auth-callback',
        'noise-delete',
        'noise-detail',
        'noise-edit',
        'noise-login',
        'noise-logout',
        'new-noise',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if self._should_track(request):
            self._track_visit(request, response)
        return response

    def _should_track(self, request):
        if not (request.path_info == '/noise' or request.path_info.startswith('/noise/')):
            return False

        resolver_match = getattr(request, 'resolver_match', None)
        if resolver_match is None:
            return request.path_info in ('/noise', '/noise/')
        return resolver_match.url_name in self.TRACKED_URL_NAMES

    def _track_visit(self, request, response):
        try:
            NoiseVisit.objects.create(
                user=self._user(request),
                noise=self._noise(request),
                path=request.get_full_path()[:1024],
                method=request.method[:12],
                status_code=getattr(response, 'status_code', None),
                ip_address=self._client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:512],
                referrer=request.META.get('HTTP_REFERER', '')[:1024],
            )
        except Exception:
            logger.exception('Could not record Noise visit')

    def _user(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            return user
        return None

    def _noise(self, request):
        resolver_match = getattr(request, 'resolver_match', None)
        noise_id = None
        if resolver_match:
            noise_id = resolver_match.kwargs.get('noise_id')
        if not noise_id:
            return None
        return Noise.objects.filter(pk=noise_id).first()

    def _client_ip(self, request):
        for header in ('HTTP_CF_CONNECTING_IP', 'HTTP_X_FORWARDED_FOR', 'REMOTE_ADDR'):
            raw_value = request.META.get(header, '')
            candidate = raw_value.split(',', 1)[0].strip()
            if not candidate:
                continue
            try:
                return str(ip_address(candidate))
            except ValueError:
                continue
        return None
