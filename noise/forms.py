from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from io import BytesIO
from PIL import Image as PILImage
from django.forms import ModelForm
from .models import Noise
from .location import COORDINATES, normalize_coordinates
from .upload_limits import (
    format_upload_size,
    get_noise_max_upload_bytes,
    validate_noise_upload_size,
)

class NoiseMediaFormMixin:
    date_added = forms.DateTimeField(
        input_formats=[
            '%Y-%m-%dT%H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
        ],
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M',
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        media_field = self.fields.get('media')
        if media_field:
            max_upload = get_noise_max_upload_bytes()
            media_field.help_text = f'Max upload: {format_upload_size(max_upload)}'
            media_field.widget.attrs.update({
                'data-max-upload-bytes': str(max_upload),
                'data-max-upload-label': format_upload_size(max_upload),
            })

    def clean_media(self):
        media = self.cleaned_data.get('media')
        validate_noise_upload_size(media)
        return media

    def clean_location(self):
        location = self.cleaned_data.get('location')
        if isinstance(location, str) and COORDINATES.match(location):
            return normalize_coordinates(location) or None
        return location


class NoiseForm(NoiseMediaFormMixin, ModelForm):

    class Meta:
        model = Noise
        fields = [
                    'media',
                    'noise_title',
                    'noise_body',
                    'noise_extras',
                    'date_added',
                    'noise_url',
                    'scrub_exif',
                    'video_loop',
                    'video_autoplay',
                    'noise_content_type',
                    'location',
                    'special_guest',
                    'bucket',
                    ]
        widgets = {
            'noise_url': forms.URLInput(attrs={'placeholder': 'https://'}),
        }
        labels = {
            'noise_title': 'Title',
            'noise_body': 'Body',
            'noise_extras': 'Extras',
            'noise_url': 'URL',
            'scrub_exif': 'Scrub EXIF metadata',
            'video_loop': 'Loop video',
            'video_autoplay': 'Autoplay video',
            'special_guest': 'Special guest',
        }


class NoiseEditForm(NoiseMediaFormMixin, ModelForm):
    class Meta:
        model = Noise
        fields = [
            'media',
            'noise_title',
            'noise_body',
            'noise_extras',
            'date_added',
            'noise_url',
            'location',
            'scrub_exif',
            'video_loop',
            'video_autoplay',
            'bucket',
            'noise_source',
            'special_guest',
        ]
        labels = {
            'noise_title': 'Title',
            'scrub_exif': 'Scrub EXIF metadata',
            'video_loop': 'Loop video',
            'video_autoplay': 'Autoplay video',
            'noise_body': 'Body',
            'noise_extras': 'Extras',
            'noise_url': 'URL',
            'noise_source': 'Source',
            'special_guest': 'Special guest',
        }
        widgets = {
            'noise_url': forms.URLInput(attrs={'placeholder': 'https://'}),
        }


class LegacyNoiseUploadForm(forms.Form):
    """Bounded, server-validated contract for the mobile legacy endpoint."""

    media = forms.FileField(required=False)
    title = forms.CharField(required=False, max_length=255)
    type = forms.ChoiceField(choices=Noise.CONTENT_TYPES)
    date = forms.IntegerField(min_value=0)
    location = forms.CharField(required=False, max_length=255)
    guest = forms.CharField(required=False, max_length=64)
    bucket = forms.ChoiceField(choices=Noise.BUCKETS)
    body = forms.CharField(required=False, max_length=8000)
    extras = forms.CharField(required=False, max_length=8000)
    url = forms.URLField(required=False, max_length=2048)
    scrub_exif = forms.BooleanField(required=False)
    video_loop = forms.BooleanField(required=False)
    video_autoplay = forms.BooleanField(required=False)

    def clean_media(self):
        media = self.cleaned_data.get('media')
        if not media:
            return media
        max_bytes = int(getattr(settings, 'NOISE_LEGACY_MAX_UPLOAD_BYTES', 20 * 1024 * 1024))
        if media.size > max_bytes:
            raise ValidationError(f'Noise uploads are limited to {max_bytes} bytes.')
        head = media.read(32)
        media.seek(0)
        if head.startswith(b'\x1a\x45\xdf\xa3'):
            self.detected_media_type = 'video'
            return media
        if len(head) >= 12 and head[4:8] == b'ftyp':
            self.detected_media_type = 'video'
            return media
        try:
            with PILImage.open(media) as image:
                image.verify()
                if image.format not in {'JPEG', 'PNG', 'GIF', 'WEBP'}:
                    raise ValidationError('Unsupported image format.')
                if image.width * image.height > 50_000_000:
                    raise ValidationError('Image dimensions are too large.')
            media.seek(0)
            self.detected_media_type = 'image'
            return media
        except (OSError, ValueError):
            media.seek(0)
            raise ValidationError('Uploaded media is not a supported image or video.')
