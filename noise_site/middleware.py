from django.conf import settings
from django.http import JsonResponse


class UploadSizeLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            content_length = int(request.META.get('CONTENT_LENGTH') or 0)
        except ValueError:
            content_length = 0
        if request.method in {'POST', 'PUT', 'PATCH'} and content_length > settings.NOISE_MAX_UPLOAD_BYTES:
            return JsonResponse({'detail': 'Upload exceeds NOISE_MAX_UPLOAD_BYTES.'}, status=413)
        return self.get_response(request)
