from django.conf import settings
from django.core.exceptions import ValidationError


DEFAULT_NOISE_MAX_UPLOAD_BYTES = 95 * 1024 * 1024


def get_noise_max_upload_bytes():
    return int(
        getattr(
            settings,
            'NOISE_MAX_UPLOAD_BYTES',
            DEFAULT_NOISE_MAX_UPLOAD_BYTES,
        )
    )


def format_upload_size(size_bytes):
    if size_bytes is None:
        return ''
    size_bytes = int(size_bytes)
    gib = 1024 ** 3
    mib = 1024 ** 2
    kib = 1024
    if size_bytes >= gib:
        value = size_bytes / gib
        unit = 'GiB'
    elif size_bytes >= mib:
        value = size_bytes / mib
        unit = 'MiB'
    elif size_bytes >= kib:
        value = size_bytes / kib
        unit = 'KiB'
    else:
        return f'{size_bytes} bytes'
    if value.is_integer():
        value = int(value)
    else:
        value = round(value, 1)
    return f'{value} {unit}'


def noise_upload_limit_message(file_size=None):
    max_upload = get_noise_max_upload_bytes()
    message = f'Noise uploads are limited to {format_upload_size(max_upload)}.'
    if file_size is not None:
        message = f'{message} Selected file is {format_upload_size(file_size)}.'
    return message


def validate_noise_upload_size(uploaded_file):
    if not uploaded_file:
        return
    file_size = getattr(uploaded_file, 'size', None)
    if file_size is None:
        return
    if int(file_size) > get_noise_max_upload_bytes():
        raise ValidationError(
            noise_upload_limit_message(file_size),
            code='file_too_large',
        )
