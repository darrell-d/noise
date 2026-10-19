import json
import shutil
import tempfile
from datetime import datetime, timedelta
from io import BytesIO
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image as PILImage

from .models import Noise
from .location import CITY, FULL, REGION, format_location
from .templatetags.gps import gps
from .templatetags.noise_markdown import noise_markdown, noise_markdown_inline


TEST_FILE_STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

def build_exif_jpeg_upload(include_datetime=True, include_gps=True):
    from PIL import Image, TiffImagePlugin

    image = Image.new('RGB', (20, 10), 'red')
    exif = Image.Exif()
    if include_datetime:
        exif[36867] = '2024:05:06 07:08:09'
    if include_gps:
        exif[34853] = {
            1: 'N',
            2: (
                TiffImagePlugin.IFDRational(39, 1),
                TiffImagePlugin.IFDRational(57, 1),
                TiffImagePlugin.IFDRational(0, 1),
            ),
            3: 'W',
            4: (
                TiffImagePlugin.IFDRational(75, 1),
                TiffImagePlugin.IFDRational(9, 1),
                TiffImagePlugin.IFDRational(0, 1),
            ),
        }

    output = BytesIO()
    image.save(output, format='JPEG', exif=exif.tobytes())
    return SimpleUploadedFile(
        'exif-photo.jpg',
        output.getvalue(),
        content_type='image/jpeg',
    )

def read_saved_image_exif(noise):
    from PIL import Image

    with noise.media.open('rb') as media_file:
        image = Image.open(media_file)
        image.load()
        return image.getexif()

def build_rgba_png_upload():
    from PIL import Image

    image = Image.new('RGBA', (20, 10), (255, 0, 0, 128))
    output = BytesIO()
    image.save(output, format='PNG')
    return SimpleUploadedFile(
        'transparent.png',
        output.getvalue(),
        content_type='image/png',
    )

def build_location_value():
    return json.dumps({
        'raw_coords': '39.9501,-75.1440',
        'details': [
            {
                'formatted_address': '225 Market St, Philadelphia, PA 19106, USA',
                'types': ['street_address'],
                'address_components': [
                    {
                        'long_name': '225',
                        'short_name': '225',
                        'types': ['street_number'],
                    },
                    {
                        'long_name': 'Market Street',
                        'short_name': 'Market St',
                        'types': ['route'],
                    },
                    {
                        'long_name': 'Philadelphia',
                        'short_name': 'Philadelphia',
                        'types': ['locality', 'political'],
                    },
                    {
                        'long_name': 'Pennsylvania',
                        'short_name': 'PA',
                        'types': ['administrative_area_level_1', 'political'],
                    },
                    {
                        'long_name': 'United States',
                        'short_name': 'US',
                        'types': ['country', 'political'],
                    },
                    {
                        'long_name': '19106',
                        'short_name': '19106',
                        'types': ['postal_code'],
                    },
                ],
            },
        ],
    })

class NoiseGpsTemplateFilterTests(TestCase):
    def test_uses_raw_coordinates_when_reverse_geocode_details_are_empty(self):
        value = json.dumps({'raw_coords': '39.95,-75.16', 'details': []})

        self.assertEqual(gps(value), '39.95,-75.16')

    def test_missing_location_uses_text_without_a_second_location_emoji(self):
        self.assertEqual(gps(None), 'Lost in the world')

    def test_prefers_neighborhood_and_ignores_plus_code(self):
        value = json.dumps({
            'raw_coords': '39.9571,-75.1556',
            'details': [
                {
                    'formatted_address': 'XR4V+RQ Philadelphia, PA, USA',
                    'types': ['plus_code'],
                },
                {
                    'formatted_address': 'Center City East, Philadelphia, PA, USA',
                    'types': ['neighborhood', 'political'],
                },
                {
                    'formatted_address': 'Philadelphia, PA, USA',
                    'types': ['locality', 'political'],
                },
            ],
        })

        self.assertEqual(gps(value), 'Center City East, Philadelphia, PA, USA')

    def test_formats_structured_location_at_each_privacy_level(self):
        value = build_location_value()

        self.assertEqual(format_location(value, REGION), 'PA, US')
        self.assertEqual(format_location(value, CITY), 'Philadelphia, PA, US')
        self.assertEqual(
            format_location(value, FULL),
            '225 Market St, Philadelphia, PA 19106, USA',
        )

    def test_uses_long_region_name_for_one_character_short_codes(self):
        value = json.dumps({
            'raw_coords': '53.3498,-6.2603',
            'details': [{
                'formatted_address': 'Dublin, Ireland',
                'types': ['locality', 'political'],
                'address_components': [
                    {
                        'long_name': 'County Dublin',
                        'short_name': 'D',
                        'types': ['administrative_area_level_1', 'political'],
                    },
                    {
                        'long_name': 'Ireland',
                        'short_name': 'IE',
                        'types': ['country', 'political'],
                    },
                ],
            }],
        })

        self.assertEqual(format_location(value, REGION), 'County Dublin, IE')

    def test_hides_raw_coordinates_from_non_admin_precision_levels(self):
        value = json.dumps({'raw_coords': '39.95,-75.16', 'details': []})

        self.assertEqual(format_location(value, REGION), 'Lost in the world')
        self.assertEqual(format_location(value, CITY), 'Lost in the world')
        self.assertEqual(format_location(value, FULL), '39.95,-75.16')

    def test_hides_null_island_coordinates_at_every_precision_level(self):
        value = json.dumps({'raw_coords': '0.000000,0.000000', 'details': []})

        self.assertEqual(format_location(value, REGION), 'Lost in the world')
        self.assertEqual(format_location(value, CITY), 'Lost in the world')
        self.assertEqual(format_location(value, FULL), 'Lost in the world')

class NoiseContentTypeInferenceTests(TestCase):
    def test_prefers_explicit_non_text_content_type(self):
        noise = Noise(
            actual_noise='abc',
            noise_content_type='fancy',
            noise_body='hello',
            location=None,
        )
        self.assertEqual(noise.infer_noise_content_type(), 'fancy')

    def test_infers_image_from_uploaded_media(self):
        media = SimpleUploadedFile('photo.jpg', b'fake image bytes', content_type='image/jpeg')
        noise = Noise(
            actual_noise='abc',
            noise_content_type='text',
            media=media,
            location=None,
        )
        self.assertEqual(noise.infer_noise_content_type(), 'image')

    def test_infers_social_from_url(self):
        noise = Noise(
            actual_noise='abc',
            noise_content_type='text',
            noise_url='https://www.instagram.com/p/example/',
            location=None,
        )
        self.assertEqual(noise.infer_noise_content_type(), 'social')

    def test_infers_rich_text_from_html_body(self):
        noise = Noise(
            actual_noise='abc',
            noise_content_type='text',
            noise_body='<p>hello</p>',
            location=None,
        )
        self.assertEqual(noise.infer_noise_content_type(), 'rich_text')

    def test_defaults_to_text_when_it_cannot_infer_more_specific_type(self):
        noise = Noise(
            actual_noise='abc',
            noise_content_type='text',
            noise_body='plain text only',
            location=None,
        )
        self.assertEqual(noise.infer_noise_content_type(), 'text')


    def test_body_preview_preserves_line_breaks(self):
        noise = Noise.objects.create(
            actual_noise='abc',
            noise_content_type='text',
            noise_body='Line one\nLine two\nLine three',
            location=None,
        )

        self.assertEqual(noise.body_preview, 'Line one\nLine two\nLine three')

    def test_body_preview_display_uses_original_body_text(self):
        noise = Noise.objects.create(
            actual_noise='abc',
            noise_content_type='text',
            noise_body='Line one\nLine two',
            location=None,
        )
        Noise.objects.filter(pk=noise.pk).update(body_preview='Line one Line two')
        noise.refresh_from_db()

        self.assertEqual(noise.body_preview_display, 'Line one\nLine two')

    def test_body_is_truncated_only_when_preview_omits_text(self):
        short_noise = Noise(noise_body='Short body')
        long_noise = Noise(noise_body=' '.join(f'word-{index}' for index in range(70)))

        self.assertFalse(short_noise.body_is_truncated)
        self.assertTrue(long_noise.body_is_truncated)

class NoiseDateAddedTests(TestCase):
    def test_date_added_defaults_and_can_be_edited(self):
        noise = Noise.objects.create(
            actual_noise='abc',
            noise_content_type='text',
            noise_body='plain text only',
            location=None,
        )
        self.assertIsNotNone(noise.date_added)

        field = Noise._meta.get_field('date_added')
        self.assertTrue(field.editable)
        self.assertFalse(field.auto_now_add)

        custom_date = timezone.now() - timedelta(days=30)
        noise.date_added = custom_date
        noise.save()
        noise.refresh_from_db()

        self.assertEqual(noise.date_added, custom_date)

class NoiseImageUploadMetadataTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.media_field = Noise._meta.get_field('media')
        self.original_media_storage = self.media_field.storage
        self.media_field.storage = FileSystemStorage(location=self.media_root)

    def tearDown(self):
        self.media_field.storage = self.original_media_storage
        shutil.rmtree(self.media_root)

    def storage_settings(self):
        return override_settings(
            DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
            STORAGES=TEST_FILE_STORAGES,
            MEDIA_ROOT=self.media_root,
            GOOGLE_MAPS_KEY='',
        )

    def test_image_upload_uses_exif_datetime_for_date_location_and_title(self):
        with self.storage_settings(), patch('noise.models.get_coord_data', return_value=[]):
            noise = Noise.objects.create(
                actual_noise='abc',
                noise_title='',
                noise_body='',
                noise_extras='',
                noise_url='',
                noise_source='',
                special_guest='',
                bucket='all',
                location=settings.HOME_GPS,
                media=build_exif_jpeg_upload(),
            )

        self.assertEqual(noise.date_added, datetime(2024, 5, 6, 7, 8, 9))
        self.assertEqual(noise.noise_title, '2024-05-06')
        self.assertTrue(noise.noise_title_generated)
        self.assertEqual(noise.noise_content_type, 'image')
        self.assertTrue(noise.media.name.endswith('.jpg'))

        location = json.loads(noise.location)
        self.assertEqual(location['raw_coords'], '39.950000,-75.150000')
        self.assertEqual(location['details'], [])

        exif = read_saved_image_exif(noise)
        self.assertEqual(exif.get(36867), '2024:05:06 07:08:09')
        self.assertIn(34853, exif)

    def test_device_location_is_fallback_when_image_has_no_exif_gps(self):
        device_date = datetime(2026, 7, 29, 12, 30)

        with self.storage_settings(), patch('noise.models.get_coord_data', return_value=[]):
            noise = Noise.objects.create(
                actual_noise='abc',
                bucket='all',
                date_added=device_date,
                location='40.000000,-75.000000',
                media=build_exif_jpeg_upload(include_gps=False),
            )

        self.assertEqual(noise.date_added, datetime(2024, 5, 6, 7, 8, 9))
        self.assertEqual(json.loads(noise.location)['raw_coords'], '40.000000,-75.000000')

    def test_null_island_device_location_is_not_saved(self):
        with self.storage_settings(), patch('noise.models.get_coord_data') as geocode:
            noise = Noise.objects.create(
                actual_noise='abc',
                bucket='public',
                location='0.000000,0.000000',
                media=build_exif_jpeg_upload(include_gps=False),
            )

        self.assertIsNone(noise.location)
        geocode.assert_not_called()

    def test_device_date_is_fallback_when_image_has_no_exif_datetime(self):
        device_date = datetime(2026, 7, 29, 12, 30)

        with self.storage_settings(), patch('noise.models.get_coord_data', return_value=[]):
            noise = Noise.objects.create(
                actual_noise='abc',
                bucket='all',
                date_added=device_date,
                location='40.000000,-75.000000',
                media=build_exif_jpeg_upload(include_datetime=False),
            )

        self.assertEqual(noise.date_added, device_date)
        self.assertEqual(json.loads(noise.location)['raw_coords'], '39.950000,-75.150000')

    def test_scrub_exif_removes_embedded_metadata_and_skips_exif_date_location(self):
        manual_date = datetime(2026, 7, 25, 11, 30)

        with self.storage_settings(), patch('noise.models.get_coord_data', return_value=[]):
            noise = Noise.objects.create(
                actual_noise='abc',
                noise_title='Manual title',
                noise_body='',
                noise_extras='',
                noise_url='',
                noise_source='',
                special_guest='',
                bucket='all',
                date_added=manual_date,
                location='40.000000,-75.000000',
                media=build_exif_jpeg_upload(),
                scrub_exif=True,
            )

        self.assertEqual(noise.date_added, manual_date)
        self.assertEqual(noise.noise_title, 'Manual title')

        location = json.loads(noise.location)
        self.assertEqual(location['raw_coords'], '40.000000,-75.000000')
        self.assertEqual(location['details'], [])

        exif = read_saved_image_exif(noise)
        self.assertFalse(exif)

    def test_existing_image_can_be_resaved_with_exif_scrubbed(self):
        with self.storage_settings(), patch('noise.models.get_coord_data', return_value=[]):
            noise = Noise.objects.create(
                actual_noise='abc',
                noise_title='Manual title',
                noise_body='',
                noise_extras='',
                noise_url='',
                noise_source='',
                special_guest='',
                bucket='all',
                location=settings.HOME_GPS,
                media=build_exif_jpeg_upload(),
            )

        self.assertTrue(read_saved_image_exif(noise))

        noise.scrub_exif = True
        with patch('noise.models.get_coord_data', return_value=[]):
            noise.save()

        self.assertFalse(read_saved_image_exif(noise))

    def test_transparent_png_upload_saves_as_jpeg_without_rgba_error(self):
        with self.storage_settings():
            noise = Noise.objects.create(
                actual_noise='abc',
                bucket='all',
                location=None,
                media=build_rgba_png_upload(),
            )

        self.assertEqual(noise.noise_content_type, 'image')
        self.assertTrue(noise.media.name.endswith('.jpg'))

class NoiseMarkdownTests(TestCase):
    def test_renders_title_markdown_inline(self):
        rendered = noise_markdown_inline('Hello **world** <script>alert(1)</script>')
        self.assertIn('<strong>world</strong>', rendered)
        self.assertNotIn('<script>', rendered)
        self.assertNotIn('<p>', rendered)

    def test_renders_body_markdown_block(self):
        rendered = noise_markdown('Line one\n\n- item one\n- item two')
        self.assertIn('<p>Line one</p>', rendered)
        self.assertIn('<li>item one</li>', rendered)

    def test_renders_single_line_breaks_in_body(self):
        rendered = noise_markdown('Line one\nLine two')

        self.assertIn('Line one<br', rendered)
        self.assertIn('Line two', rendered)

    def test_escapes_raw_html_in_body(self):
        rendered = noise_markdown('<img src=x onerror=alert(1)>')
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', rendered)
