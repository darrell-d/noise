import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from noise.models import Noise


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class StandaloneTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_superuser('owner', 'owner@example.com', 'test-password')
        cls.reader = users.objects.create_user('reader', password='test-password')
        cls.public = Noise.objects.create(noise_body='Public message', bucket='public')
        cls.private = Noise.objects.create(noise_body='Private message', bucket='personal')
        cls.restricted = Noise.objects.create(noise_body='Restricted message', bucket='pg_13')

    def test_public_feed_and_detail(self):
        self.assertRedirects(self.client.get('/'), '/noise/')
        response = self.client.get('/noise/')
        self.assertContains(response, 'Public message')
        self.assertNotContains(response, 'Private message')
        self.assertNotContains(response, 'Restricted message')
        self.assertEqual(self.client.get(self.public.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(self.private.get_absolute_url()).status_code, 404)

    def test_local_login_and_staff_editor(self):
        self.assertEqual(self.client.get(reverse('noise-add')).status_code, 302)
        response = self.client.post('/accounts/login/', {'username': 'owner', 'password': 'test-password'})
        self.assertRedirects(response, '/noise/')
        self.assertEqual(self.client.get(reverse('noise-add')).status_code, 200)
        self.assertEqual(self.client.get('/admin/noise/noise/').status_code, 200)
        response = self.client.post(reverse('noise-add'), {
            'noise_body': 'A fresh transmission', 'bucket': 'public',
            'noise_content_type': 'text',
            'date_added': '2026-10-19T10:00',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Noise.objects.filter(noise_body='A fresh transmission').exists())
        self.assertContains(self.client.get('/noise/'), 'Private message')

    def test_group_access_and_api_write_permissions(self):
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(self.restricted.get_absolute_url()).status_code, 404)
        self.reader.groups.add(Group.objects.create(name='PG-13'))
        self.assertEqual(self.client.get(self.restricted.get_absolute_url()).status_code, 200)
        response = self.client.get('/api/noise/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Private message')
        self.assertEqual(self.client.post('/api/noise/', {'noise_body': 'Unauthorized'}).status_code, 403)
        self.assertEqual(self.client.delete(f'/api/noise/{self.public.pk}/').status_code, 403)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post('/api/noise/', {'noise_body': 'API post'}).status_code, 201)

    def test_owner_bucket_choices_and_no_personal_email_grants(self):
        self.assertIn('personal', [choice['value'] for choice in Noise.bucket_choices_for_user(self.owner)])
        self.assertNotIn('personal', [choice['value'] for choice in Noise.bucket_choices_for_user(self.reader)])
        self.assertEqual(Noise.PARAMOUR_EMAILS, ())

    def test_local_media_checks_bucket_permissions_and_paths(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            upload = SimpleUploadedFile('private.txt', b'private file', content_type='text/plain')
            post = Noise.objects.create(bucket='personal', media=upload)
            url = post.media.url
            self.assertEqual(self.client.get(url).status_code, 404)
            self.client.force_login(self.owner)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'private file')
            self.assertEqual(response['Content-Disposition'], 'attachment')
            self.assertEqual(response['Cache-Control'], 'private, no-store')
            self.client.force_login(self.reader)
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.get('/media/../.env').status_code, 404)

    def test_social_callback_rejects_missing_state(self):
        self.assertRedirects(self.client.get('/noise/auth/callback/'), '/noise/')

    def test_login_next_rejects_external_host(self):
        response = self.client.post('/accounts/login/?next=https://example.com/', {
            'username': 'owner', 'password': 'test-password', 'next': 'https://example.com/',
        })
        self.assertRedirects(response, '/noise/')

    @override_settings(NOISE_MAX_UPLOAD_BYTES=10)
    def test_upload_limit(self):
        self.assertEqual(self.client.post('/api/noise/', {'noise_body': 'Too much data'}).status_code, 413)

    def test_visits_are_opt_in(self):
        from noise.models import NoiseVisit
        self.client.get('/noise/')
        self.assertFalse(NoiseVisit.objects.exists())

    @override_settings(AWS_STORAGE_BUCKET_NAME='noise-test', AWS_ACCESS_KEY_ID='test', AWS_SECRET_ACCESS_KEY='test')
    def test_s3_uploads_work_without_object_acls(self):
        from unittest.mock import patch
        from storages.backends.s3boto3 import S3Boto3Storage
        from noise.storage import NoiseMediaStorage, PRIVATE_CACHE_CONTROL

        with patch('noise.storage.default_storage', S3Boto3Storage()):
            backend = NoiseMediaStorage()._backend()
            parameters = backend._get_write_parameters('noise/test.txt')
        self.assertNotIn('ACL', parameters)
        self.assertEqual(parameters['CacheControl'], PRIVATE_CACHE_CONTROL)
        self.assertTrue(backend.querystring_auth)
        self.assertEqual(backend.querystring_expire, 300)

    def test_csrf_required_for_api_writes(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        response = client.post('/api/noise/', {'noise_body': 'No CSRF token'})
        self.assertEqual(response.status_code, 403)
