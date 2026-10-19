from django.core.files.storage import Storage, default_storage
from django.utils.deconstruct import deconstructible
from storages.backends.s3boto3 import S3Boto3Storage


PRIVATE_CACHE_CONTROL = "private, max-age=300"


@deconstructible
class NoiseMediaStorage(Storage):
    """Use private, expiring S3 objects while preserving local test storage."""

    def __init__(self):
        self._private_s3 = None

    def _backend(self):
        if isinstance(default_storage, S3Boto3Storage):
            if self._private_s3 is None:
                self._private_s3 = S3Boto3Storage(
                    default_acl=None,
                    querystring_auth=True,
                    querystring_expire=300,
                    object_parameters={"CacheControl": PRIVATE_CACHE_CONTROL},
                )
            return self._private_s3
        return default_storage

    def _open(self, name, mode="rb"):
        return self._backend().open(name, mode)

    def _save(self, name, content):
        return self._backend().save(name, content)

    def delete(self, name):
        return self._backend().delete(name)

    def exists(self, name):
        return self._backend().exists(name)

    def listdir(self, path):
        return self._backend().listdir(path)

    def size(self, name):
        return self._backend().size(name)

    def url(self, name):
        backend = self._backend()
        if isinstance(backend, S3Boto3Storage):
            return backend.url(
                name,
                parameters={"ResponseCacheControl": PRIVATE_CACHE_CONTROL},
            )
        return backend.url(name)


noise_media_storage = NoiseMediaStorage()
