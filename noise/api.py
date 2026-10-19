from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.response import Response

from .models import Noise
from .serializers import NoiseSerializer


class NoisePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and (request.method in SAFE_METHODS or user.is_staff))


class NoiseViewSet(viewsets.ModelViewSet):
    queryset = Noise.objects.none()
    serializer_class = NoiseSerializer
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    permission_classes = [NoisePermission]

    def get_queryset(self):
        return Noise.visible_queryset_for_user(self.request.user)

    @action(detail=False, methods=['get'], url_path='buckets')
    def buckets(self, request):
        if request.query_params.get('scope') == 'posting':
            return Response(Noise.posting_bucket_choices())
        return Response(Noise.bucket_choices_for_user(request.user))
