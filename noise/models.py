import os
from django.db import models
from django.conf import settings
from django.contrib.auth.models import Group
from .utils import is_json, get_coord_data
from .location import COORDINATES, normalize_coordinates

import requests
import logging

import json
import re
import secrets
import unicodedata
from datetime import datetime
from urllib.parse import urlparse

from PIL import ExifTags, Image
from django.core.files.uploadedfile import InMemoryUploadedFile  
from io import BytesIO
from django.utils import timezone
from django.urls import reverse

from .storage import noise_media_storage

logger = logging.getLogger(__name__)


def nist_random():
    return secrets.token_hex(32)



class Noise(models.Model):
    ADMIN_TITLE_MAX_LENGTH = 128
    OWNER_EMAIL = ''
    PUBLIC_BUCKET = 'public'
    AUTHENTICATED_BUCKET = 'g'
    PERSONAL_BUCKET = 'personal'
    PARAMOUR_BUCKET = 'paramour'
    PUBLIC_BUCKET_ALIASES = ('public', 'all')
    AUTHENTICATED_BUCKET_ALIASES = ('g', 'family')
    PARAMOUR_EMAILS = ()
    RESTRICTED_BUCKET_GROUPS = {
        'pg_13': 'PG-13',
        'r': 'R',
        'ma': 'MA',
        PARAMOUR_BUCKET: 'Paramour',
    }
    ORDERING = ('-date_added',)
    EXIF_DATE_TAGS = (36867, 36868, 306)
    EXIF_GPS_TAG = 34853
    GENERATED_TITLE_SOURCE_FIELDS = (
        'noise_body',
        'noise_extras',
        'noise_url',
        'noise_source',
        'special_guest',
    )

    CONTENT_TYPES = [
            ('video', 'Video'),
            ('image', 'Image'),
            ('text', 'Text'),
            ('rich_text', 'Rich Text'),
            ('social', 'Social'),
            ('link', 'Link'),
            ('downloadable', 'Downloadable'),
            ('fancy', 'Fancy')
            ]

    BUCKETS = [
        ('public', 'Public'),
        ('g', 'G'),
        ('pg_13', 'PG-13'),
        ('r', 'R'),
        ('ma', 'MA'),
        (PARAMOUR_BUCKET, 'Paramour'),
        ('personal', 'Personal'),
    ]
    noise_title = models.CharField(max_length=255, null=True, blank=True)
    noise_title_generated = models.BooleanField(default=False)
    actual_noise = models.CharField(max_length=128, null=False, blank=False, default=nist_random)
    noise_content_type = models.CharField(max_length=32, choices=CONTENT_TYPES, default='text', null=False, blank=False)
    published_date = models.DateTimeField('date published',auto_now_add=True)
    date_added = models.DateTimeField('date added', default=timezone.now)
    location = models.TextField(default=settings.HOME_GPS, null=True, blank=True)
    noise_maker = models.CharField(max_length=64, default='noise')
    special_guest = models.CharField(max_length=64, null=True, blank=True)
    bucket = models.CharField(max_length=255, choices=BUCKETS, default=PUBLIC_BUCKET)
    noise_body = models.TextField(null=True, blank=True)
    noise_url = models.TextField(null=True, blank=True)
    noise_source = models.CharField(max_length=255, null=True, blank=True)
    noise_extras = models.TextField(null=True, blank=True)
    media = models.FileField(
        null=True,
        blank=True,
        upload_to=settings.NOISE_MEDIA_FOLDER,
        storage=noise_media_storage,
    )
    scrub_exif = models.BooleanField(
        default=False,
        help_text='Remove embedded metadata from uploaded image files and skip EXIF date/location extraction.',
    )
    video_loop = models.BooleanField(default=False)
    video_autoplay = models.BooleanField(default=False)
    is_tall = models.BooleanField(default=False, null=True, blank=True)
    body_preview = models.TextField(default='', null=True, blank=True)

    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tif', '.tiff'}
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.m4v', '.webm', '.avi', '.mkv'}
    DOWNLOADABLE_EXTENSIONS = {'.pdf', '.zip', '.rar', '.7z', '.txt', '.csv', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'}
    SOCIAL_HOSTS = {
        'twitter.com',
        'x.com',
        'www.twitter.com',
        'www.x.com',
        'instagram.com',
        'www.instagram.com',
        'tiktok.com',
        'www.tiktok.com',
        'facebook.com',
        'www.facebook.com',
        'youtu.be',
        'youtube.com',
        'www.youtube.com',
        'vimeo.com',
        'www.vimeo.com',
    }

    def __str__(self):
        return self.display_title

    @property
    def display_title(self):
        title = self._trim_display_title(self.noise_title)
        if title and not self._title_matches_actual_noise(title):
            return title

        return self.generated_title

    @property
    def generated_title(self):
        return self._build_display_title(self.GENERATED_TITLE_SOURCE_FIELDS)

    @property
    def public_title(self):
        title = self._trim_display_title(self.noise_title)
        if (
            not title
            or self.noise_title_generated
            or self._title_matches_actual_noise(title)
            or title == self._date_display_title()
        ):
            return ''
        return title

    @property
    def public_extras(self):
        extras = (self.noise_extras or '').strip()
        if extras and is_json(extras):
            return ''
        return extras

    @property
    def share_key(self):
        key = re.sub(r'[^a-zA-Z0-9]+', '', self.actual_noise or '').lower()
        return key[:12] or 'noise'

    def get_absolute_url(self):
        return reverse('noise-detail', args=[self.share_key, self.pk])

    @property
    def body_preview_display(self):
        return self._build_body_preview()

    @property
    def body_is_truncated(self):
        if not self.noise_body:
            return False
        return self.body_preview_display != self.noise_body.strip()

    @property
    def public_media_url(self):
        external_url = (self.noise_url or '').strip()
        if external_url:
            if external_url.startswith(('http://', 'https://', '/')):
                return external_url
            return f'https://{external_url}'
        if not self.media:
            return ''
        try:
            return self.media.url
        except ValueError:
            return ''

    def _build_display_title(self, field_names):
        for field_name in field_names:
            value = self.public_extras if field_name == 'noise_extras' else getattr(self, field_name, None)
            title = self._trim_display_title(value)
            if title:
                return title

        return self._date_display_title()

    def _date_display_title(self):
        title_date = self.date_added or self.published_date or timezone.now()
        if timezone.is_aware(title_date):
            title_date = timezone.localtime(title_date)
        return title_date.strftime('%Y-%m-%d')

    @classmethod
    def _trim_display_title(cls, value):
        if value is None:
            return ''
        normalized = ' '.join(str(value).split())
        trimmed = []
        character_count = 0
        for cluster in cls._text_clusters(normalized):
            if cluster.isspace():
                if trimmed and character_count < cls.ADMIN_TITLE_MAX_LENGTH:
                    trimmed.append(cluster)
                continue
            if character_count >= cls.ADMIN_TITLE_MAX_LENGTH:
                break
            trimmed.append(cluster)
            character_count += 1
        return ''.join(trimmed)

    @classmethod
    def _text_clusters(cls, value):
        clusters = []
        current_cluster = ''
        join_next = False
        regional_indicator_count = 0

        for char in value:
            codepoint = ord(char)
            is_regional_indicator = 0x1F1E6 <= codepoint <= 0x1F1FF
            attaches_to_previous = (
                unicodedata.combining(char)
                or 0xFE00 <= codepoint <= 0xFE0F
                or 0x1F3FB <= codepoint <= 0x1F3FF
                or codepoint == 0x20E3
                or codepoint == 0x200D
            )

            if not current_cluster:
                current_cluster = char
                regional_indicator_count = 1 if is_regional_indicator else 0
            elif (
                join_next
                or attaches_to_previous
                or (is_regional_indicator and regional_indicator_count % 2 == 1)
            ):
                current_cluster += char
                if is_regional_indicator:
                    regional_indicator_count += 1
                elif not attaches_to_previous:
                    regional_indicator_count = 0
            else:
                clusters.append(current_cluster)
                current_cluster = char
                regional_indicator_count = 1 if is_regional_indicator else 0

            join_next = codepoint == 0x200D

        if current_cluster:
            clusters.append(current_cluster)

        return clusters

    def _title_matches_actual_noise(self, title):
        return bool(self.actual_noise and title == self._trim_display_title(self.actual_noise))

    def _should_generate_noise_title(self, current_title):
        if not current_title or self._title_matches_actual_noise(current_title):
            return True

        if not self.pk:
            return False

        previous_noise = (
            type(self).objects
            .filter(pk=self.pk)
            .only(
                'actual_noise',
                'noise_title',
                'noise_title_generated',
                'noise_body',
                'noise_extras',
                'noise_url',
                'noise_source',
                'special_guest',
                'date_added',
                'published_date',
            )
            .first()
        )
        if previous_noise is None:
            return False

        previous_title = self._trim_display_title(previous_noise.noise_title)
        if previous_noise.noise_title_generated:
            return current_title == previous_title

        return current_title == previous_title == previous_noise.generated_title

    def update_noise_title(self):
        current_title = self._trim_display_title(self.noise_title)
        if self._should_generate_noise_title(current_title):
            self.noise_title = self.generated_title
            self.noise_title_generated = True
        else:
            self.noise_title = current_title
            self.noise_title_generated = False

    @classmethod
    def public_queryset(cls):
        return cls.objects.filter(
            bucket__in=cls.PUBLIC_BUCKET_ALIASES,
        ).order_by(*cls.ORDERING)

    @classmethod
    def is_public_bucket(cls, bucket):
        return bucket in cls.PUBLIC_BUCKET_ALIASES

    @classmethod
    def visible_queryset_for_user(cls, user):
        if not (user.is_authenticated and user.is_active):
            return cls.public_queryset()

        if user.is_superuser:
            return cls.objects.all().order_by(*cls.ORDERING)

        allowed_buckets = [
            *cls.PUBLIC_BUCKET_ALIASES,
            *cls.AUTHENTICATED_BUCKET_ALIASES,
        ]
        user_group_names = set(user.groups.values_list('name', flat=True))
        allowed_buckets.extend(
            bucket
            for bucket, group_name in cls.RESTRICTED_BUCKET_GROUPS.items()
            if group_name in user_group_names
        )
        return cls.objects.filter(bucket__in=allowed_buckets).order_by(*cls.ORDERING)

    @classmethod
    def bucket_choices_for_user(cls, user):
        choices_by_bucket = dict(cls.BUCKETS)
        if not (user.is_authenticated and user.is_active):
            return [
                {'value': bucket, 'label': choices_by_bucket[bucket]}
                for bucket in cls.PUBLIC_BUCKET_ALIASES
                if bucket in choices_by_bucket
            ]

        if user.is_superuser:
            return [
                {'value': bucket, 'label': label}
                for bucket, label in cls.BUCKETS
            ]

        allowed_buckets = [
            bucket for bucket in cls.PUBLIC_BUCKET_ALIASES + cls.AUTHENTICATED_BUCKET_ALIASES
            if bucket in choices_by_bucket
        ]
        user_group_names = set(user.groups.values_list('name', flat=True))
        allowed_buckets.extend(
            bucket
            for bucket, group_name in cls.RESTRICTED_BUCKET_GROUPS.items()
            if bucket in choices_by_bucket and group_name in user_group_names
        )
        return [
            {'value': bucket, 'label': choices_by_bucket[bucket]}
            for bucket in dict.fromkeys(allowed_buckets)
        ]

    @classmethod
    def posting_bucket_choices(cls):
        return [
            {'value': bucket, 'label': label}
            for bucket, label in cls.BUCKETS
        ]

    @classmethod
    def assign_default_groups_for_user(cls, user):
        email = (getattr(user, 'email', '') or '').strip().casefold()
        if email not in cls.PARAMOUR_EMAILS:
            return
        group_name = cls.RESTRICTED_BUCKET_GROUPS[cls.PARAMOUR_BUCKET]
        group, _created = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)

    def infer_noise_content_type(self):
        current_type = self.noise_content_type or ''
        if current_type and current_type != 'text':
            return current_type

        media_candidate = self._infer_from_media()
        if media_candidate:
            return media_candidate

        url_candidate = self._infer_from_url()
        if url_candidate:
            return url_candidate

        body_candidate = self._infer_from_body()
        if body_candidate:
            return body_candidate

        return 'text'

    def _infer_from_media(self):
        if not self.media:
            return None
        content_type = getattr(self.media, 'content_type', '') or ''
        base_name = os.path.basename(self.media.name or '')
        _, file_ext = os.path.splitext(base_name.lower())
        if content_type.startswith('image/') or file_ext in self.IMAGE_EXTENSIONS:
            return 'image'
        if content_type.startswith('video/') or file_ext in self.VIDEO_EXTENSIONS:
            return 'video'
        if file_ext in self.DOWNLOADABLE_EXTENSIONS:
            return 'downloadable'
        return None

    def _infer_from_url(self):
        candidate_url = self.noise_url or self.noise_source or ''
        if not candidate_url:
            return None

        parsed = urlparse(candidate_url)
        haystack = f"{parsed.netloc}{parsed.path}".lower()
        _, file_ext = os.path.splitext(parsed.path.lower())

        if any(host in haystack for host in self.SOCIAL_HOSTS):
            return 'social'
        if file_ext in self.IMAGE_EXTENSIONS:
            return 'image'
        if file_ext in self.VIDEO_EXTENSIONS:
            return 'video'
        if file_ext in self.DOWNLOADABLE_EXTENSIONS:
            return 'downloadable'
        if parsed.scheme or parsed.netloc:
            return 'link'
        return None

    def _infer_from_body(self):
        if not self.noise_body:
            return None
        body = self.noise_body.strip()
        if '<' in body and '>' in body:
            return 'rich_text'
        return None

    def _has_uncommitted_media(self):
        return bool(self.media and not getattr(self.media, '_committed', True))

    def _media_is_image(self):
        if not self.media:
            return False

        content_type = getattr(self.media, 'content_type', '') or ''
        base_name = os.path.basename(self.media.name or '')
        _, file_ext = os.path.splitext(base_name)
        return content_type.startswith('image/') or file_ext.lower() in self.IMAGE_EXTENSIONS

    @classmethod
    def _parse_exif_datetime(cls, value):
        if not value:
            return None

        normalized = str(value).strip().replace('\x00', '')
        for fmt in ('%Y:%m:%d %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
            try:
                return datetime.strptime(normalized[:19], fmt)
            except ValueError:
                pass
        return None

    @classmethod
    def _extract_exif_datetime(cls, exif):
        if not exif:
            return None

        for tag in cls.EXIF_DATE_TAGS:
            parsed = cls._parse_exif_datetime(exif.get(tag))
            if parsed:
                return parsed
        return None

    @classmethod
    def _rational_to_float(cls, value):
        if hasattr(value, 'numerator') and hasattr(value, 'denominator'):
            if value.denominator:
                return value.numerator / value.denominator
            return 0.0

        if isinstance(value, (tuple, list)) and len(value) == 2:
            numerator, denominator = value
            if denominator:
                return numerator / denominator
            return 0.0

        return float(value)

    @classmethod
    def _gps_reference(cls, reference):
        if isinstance(reference, bytes):
            try:
                return reference.decode('ascii').strip().upper()
            except UnicodeDecodeError:
                return ''
        return str(reference).strip().upper()

    @classmethod
    def _degrees_to_decimal(cls, values, reference):
        if not values or len(values) < 3:
            return None

        degrees = cls._rational_to_float(values[0])
        minutes = cls._rational_to_float(values[1])
        seconds = cls._rational_to_float(values[2])
        decimal = degrees + (minutes / 60) + (seconds / 3600)
        if cls._gps_reference(reference) in ('S', 'W'):
            decimal *= -1
        return decimal

    @classmethod
    def _extract_exif_gps(cls, exif):
        if not exif:
            return ''

        gps_info = None
        try:
            gps_info = exif.get_ifd(cls.EXIF_GPS_TAG)
        except (AttributeError, KeyError, TypeError):
            pass

        if not gps_info:
            gps_info = exif.get(cls.EXIF_GPS_TAG)
        if not isinstance(gps_info, dict):
            return ''

        gps = {
            ExifTags.GPSTAGS.get(tag, tag): value
            for tag, value in gps_info.items()
        }
        latitude = cls._degrees_to_decimal(
            gps.get('GPSLatitude'),
            gps.get('GPSLatitudeRef'),
        )
        longitude = cls._degrees_to_decimal(
            gps.get('GPSLongitude'),
            gps.get('GPSLongitudeRef'),
        )

        if latitude is None or longitude is None:
            return ''
        return normalize_coordinates(f'{latitude:.6f},{longitude:.6f}')

    @classmethod
    def _extract_exif_bytes(cls, image):
        exif_bytes = image.info.get('exif')
        if exif_bytes:
            return exif_bytes

        try:
            exif = image.getexif()
        except (AttributeError, OSError, TypeError, ValueError):
            return None

        if not exif:
            return None

        try:
            return exif.tobytes()
        except (OSError, TypeError, ValueError):
            logger.warning('Could not serialize EXIF metadata for Noise upload', exc_info=True)
            return None

    @classmethod
    def _image_as_jpeg_file(cls, image, file_root, preserve_exif=True):
        image.load()
        exif_bytes = cls._extract_exif_bytes(image) if preserve_exif else None

        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
            rgba_image = image.convert('RGBA')
            background = Image.new('RGB', rgba_image.size, (255, 255, 255))
            background.paste(rgba_image, mask=rgba_image.getchannel('A'))
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        output = BytesIO()
        save_kwargs = {
            'format': 'JPEG',
            'quality': 75,
        }
        if preserve_exif and exif_bytes:
            save_kwargs['exif'] = exif_bytes

        image.save(output, **save_kwargs)
        output.seek(0)

        return InMemoryUploadedFile(
            output,
            'ImageField',
            f'{file_root}.jpg',
            'image/jpeg',
            output.getbuffer().nbytes,
            None,
        )

    def _apply_uploaded_image_metadata(self, image):
        exif = image.getexif()
        exif_datetime = self._extract_exif_datetime(exif)
        exif_gps = self._extract_exif_gps(exif)

        if exif_datetime:
            self.date_added = exif_datetime
        if exif_gps:
            self.location = exif_gps

    def _prepare_uploaded_image(self):
        base_name = os.path.basename(self.media.name or '')
        file_root, _file_ext = os.path.splitext(base_name)
        file_root = file_root or 'noise'
        image = Image.open(self.media)

        if not self.scrub_exif:
            self._apply_uploaded_image_metadata(image)
        self.media = self._image_as_jpeg_file(
            image,
            file_root,
            preserve_exif=not self.scrub_exif,
        )

    def _should_scrub_existing_media(self):
        if not self.pk or not self.scrub_exif or not self.media or not self._media_is_image():
            return False

        previous_noise = (
            type(self).objects
            .filter(pk=self.pk)
            .only('media', 'scrub_exif')
            .first()
        )
        return bool(
            previous_noise
            and previous_noise.media
            and previous_noise.media.name == self.media.name
            and not previous_noise.scrub_exif
        )

    def _scrub_existing_media(self):
        base_name = os.path.basename(self.media.name or '')
        file_root, _file_ext = os.path.splitext(base_name)
        file_root = file_root or 'noise'

        self.media.open('rb')
        original_media = self.media
        try:
            image = Image.open(original_media)
            self.media = self._image_as_jpeg_file(image, file_root, preserve_exif=False)
        finally:
            try:
                original_media.close()
            except AttributeError:
                pass

    def _build_body_preview(self):
        if not self.noise_body:
            return ''

        body = self.noise_body.strip()
        words_seen = 0
        preview_end = 0
        in_word = False

        for index, char in enumerate(body):
            if char.isspace():
                in_word = False
            elif not in_word:
                words_seen += 1
                in_word = True

            if words_seen > 63:
                break
            preview_end = index + 1

        preview = body[:preview_end].rstrip()
        if preview_end < len(body):
            preview = f'{preview} ...'
        return preview

    def save(self, *args, **kwargs):
        self.noise_content_type = self.infer_noise_content_type()

        if self._has_uncommitted_media() and self._media_is_image():
            self._prepare_uploaded_image()
        elif self._should_scrub_existing_media():
            self._scrub_existing_media()

        self.update_noise_title()
        # Check to see if primitive GPS coordinates or complex coords
        if not is_json(self.location) and self.location not in [None, '']:
            location_text = str(self.location).strip()
            if COORDINATES.match(location_text):
                self.location = normalize_coordinates(location_text) or None

            # Not JSON assumes first time save, build out complex coords
            if self.location:
                gps_data = {}
                gps_data['raw_coords'] = self.location
                gps_data['details'] = get_coord_data(gps_data['raw_coords'])
                self.location = json.dumps(gps_data)

        #  Check if content is tall
        if self.noise_body:
            word_count = len(self.noise_body.split())
            if word_count > 50:
                self.is_tall = True

        # Set preview of body text
        self.body_preview = self._build_body_preview()

        # Get primitive coords
        # Make request to Maps API
        # Save JSON object
        super().save(*args, **kwargs)


class TetrisScore(models.Model):
    name = models.CharField(max_length=16)
    score = models.PositiveIntegerField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-score', 'created_at')

    def __str__(self):
        return f'{self.name}: {self.score}'


class NoiseVisit(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='noise_visits',
    )
    noise = models.ForeignKey(
        Noise,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visits',
    )
    path = models.CharField(max_length=1024)
    method = models.CharField(max_length=12)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    referrer = models.CharField(max_length=1024, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('created_at',), name='noisevisit_created_idx'),
            models.Index(fields=('path', 'created_at'), name='noisevisit_path_created_idx'),
            models.Index(fields=('user', 'created_at'), name='noisevisit_user_created_idx'),
            models.Index(fields=('noise', 'created_at'), name='noisevisit_noise_created_idx'),
        ]

    def __str__(self):
        identity = self.user.email if self.user and self.user.email else self.ip_address or 'anonymous'
        return f'{identity} {self.method} {self.path}'
