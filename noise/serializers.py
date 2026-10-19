from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError

from .location import location_for_user
from .models import Noise
from .upload_limits import validate_noise_upload_size


class NoiseSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Noise
        fields = [
            'id',
            'noise_title',
            'actual_noise',
            'noise_content_type',
            'published_date',
            'date_added',
            'location',
            'noise_maker',
            'special_guest',
            'bucket',
            'noise_body',
            'noise_url',
            'noise_source',
            'noise_extras',
            'media',
            'media_url',
            'scrub_exif',
            'video_loop',
            'video_autoplay',
            'is_tall',
            'body_preview',
        ]
        read_only_fields = [
            'id',
            'actual_noise',
            'published_date',
            'is_tall',
            'body_preview',
            'media_url',
        ]
        extra_kwargs = {
            'media': {'write_only': True},
        }

    def get_media_url(self, obj):
        return obj.public_media_url or None

    def validate_media(self, value):
        try:
            validate_noise_upload_size(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated and user.is_active and user.is_staff):
            data['noise_title'] = instance.public_title
            data['noise_extras'] = instance.public_extras or None
        data['location'] = (
            location_for_user(instance.location, user)
            if instance.location not in (None, '')
            else None
        )
        return data
