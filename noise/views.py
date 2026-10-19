from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from noise.models import Noise, TetrisScore
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import Http404
from django.http import JsonResponse
from datetime import datetime
from django.utils.timezone import activate

import pytz

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST

from .forms import LegacyNoiseUploadForm, NoiseEditForm, NoiseForm
from .location import COORDINATES
from .upload_limits import validate_noise_upload_size
import logging
from io import BytesIO
from PIL import Image as PILImage
from PIL import ImageFilter, ImageOps

from django.conf import settings

logger = logging.getLogger(__name__)


UNDATED_YEAR_LABEL = '0000'
TRUTHY_FORM_VALUES = {'1', 'true', 't', 'yes', 'y', 'on'}

def addMediaPath(n):
    n.media = '{}/{}'.format(settings.NOISE_MEDIA_FOLDER, n.media) 
    return n


def _noise_year_label(noise):
    noise_date = noise.date_added or noise.published_date
    if not noise_date:
        return UNDATED_YEAR_LABEL
    return str(noise_date.year)


def _group_noises_by_year(noises):
    buckets = {}
    for noise in noises:
        label = _noise_year_label(noise)
        buckets.setdefault(label, []).append(noise)

    years = sorted([label for label in buckets if label != UNDATED_YEAR_LABEL], reverse=True)
    if UNDATED_YEAR_LABEL in buckets:
        years.append(UNDATED_YEAR_LABEL)

    return [{'label': label, 'noises': buckets[label]} for label in years], years


def _truthy_post_value(value):
    return str(value or '').strip().lower() in TRUTHY_FORM_VALUES


@ensure_csrf_cookie
def index(request):
    noise = list(Noise.visible_queryset_for_user(request.user))
    groups, years = _group_noises_by_year(noise)
    current_year = str(datetime.now().year)
    archive_gate_added = False
    for group in groups:
        group['archive_locked'] = (
            not request.user.is_authenticated
            and group['label'] != current_year
        )
        group['show_archive_gate'] = (
            group['archive_locked']
            and not archive_gate_added
        )
        if group['archive_locked']:
            group['archive_previews'] = [
                {
                    'id': item.id,
                    'has_image': (
                        item.noise_content_type == 'image'
                        and bool(item.media)
                    ),
                }
                for item in group['noises']
            ]
            # Do not expose locked post objects to the template. Their text and
            # original media URLs must never enter an anonymous response.
            group['noises'] = []
        archive_gate_added = archive_gate_added or group['show_archive_gate']
    seed_items = noise if request.user.is_authenticated else [
        item for item in noise if _noise_year_label(item) == current_year
    ]
    noise_life_seeds = [
        item.actual_noise
        for item in seed_items
        if Noise.is_public_bucket(item.bucket) and item.actual_noise
    ][:3]
    # [addMediaPath(_n) for _n in noise if _n.media]

    return render(request, 'noise/noise.html', {
        'noises': noise,
        'groups': groups,
        'year_nav': years,
        'noise_life_seeds': noise_life_seeds,
        })


def detail(request, noise_key, noise_id):
    noise = get_object_or_404(
        Noise.visible_queryset_for_user(request.user),
        pk=noise_id,
    )
    if noise_key != noise.share_key:
        return redirect(noise.get_absolute_url(), permanent=True)

    noise_life_seeds = list(
        Noise.public_queryset()
        .exclude(actual_noise='')
        .values_list('actual_noise', flat=True)[:3]
    )
    return render(request, 'noise/noise.html', {
        'noises': [noise],
        'groups': [{
            'label': _noise_year_label(noise),
            'noises': [noise],
        }],
        'year_nav': [],
        'noise_life_seeds': noise_life_seeds,
        'noise_detail': True,
    })


def _serialize_tetris_scores():
    return [
        {'name': entry.name, 'score': entry.score}
        for entry in TetrisScore.objects.all()[:10]
    ]


@require_http_methods(['GET', 'POST'])
def tetris_scores(request):
    if request.method == 'GET':
        return JsonResponse({'scores': _serialize_tetris_scores()})

    name = ' '.join(request.POST.get('name', '').split())[:16]
    try:
        score = int(request.POST.get('score', ''))
    except (TypeError, ValueError):
        score = 0

    if not name or not 0 < score <= 10_000_000:
        return JsonResponse({'error': 'Enter a name and a valid score.'}, status=400)

    with transaction.atomic():
        entry = TetrisScore.objects.create(name=name, score=score)
        top_ids = list(TetrisScore.objects.values_list('id', flat=True)[:10])
        TetrisScore.objects.exclude(id__in=top_ids).delete()
        position = top_ids.index(entry.id) + 1 if entry.id in top_ids else None

    return JsonResponse({
        'position': position,
        'scores': _serialize_tetris_scores(),
    }, status=201)


@staff_member_required(login_url='/accounts/login/')
def add(request):

    if request.method == 'POST':
        form = NoiseForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            _form = NoiseForm()
            return render(request, 'noise/add.html', {'form': _form, 'status': 'success'})
        response_status = 413 if 'media' in form.errors else 200
        return render(
            request,
            'noise/add.html',
            {'form': form, 'status': 'error'},
            status=response_status,
        )

    else:
        form = NoiseForm()

    return render(request, 'noise/add.html', {'form': form})


@staff_member_required(login_url='/accounts/login/')
def edit(request, noise_id):
    noise = get_object_or_404(Noise, pk=noise_id)

    if request.method == 'POST':
        form = NoiseEditForm(request.POST, request.FILES, instance=noise)
        if form.is_valid():
            form.save()
            messages.success(request, 'Saved.')
            return HttpResponseRedirect(reverse('noise-edit', args=[noise.id]))
    else:
        form = NoiseEditForm(instance=noise)

    return render(request, 'noise/edit.html', {
        'form': form,
        'noise': noise,
    })


@staff_member_required(login_url='/accounts/login/')
@require_POST
def delete(request, noise_id):
    noise = get_object_or_404(Noise, pk=noise_id)
    noise.delete()
    messages.success(request, 'Noise deleted.')
    return HttpResponseRedirect('/noise/')


@staff_member_required(login_url='/accounts/login/')
def admin_thumbnail(request, noise_id):
    noise = get_object_or_404(Noise, pk=noise_id)
    if not noise.media or noise.noise_content_type != 'image':
        raise Http404
    try:
        noise.media.open('rb')
        with PILImage.open(noise.media) as image:
            image.thumbnail((112, 84), PILImage.Resampling.LANCZOS)
            output = BytesIO()
            image.convert('RGB').save(output, 'JPEG', quality=58, optimize=True)
    except (OSError, ValueError):
        raise Http404
    finally:
        noise.media.close()
    response = HttpResponse(output.getvalue(), content_type='image/jpeg')
    response['Cache-Control'] = 'private, max-age=604800'
    return response


def archive_preview(request, noise_id):
    noise = get_object_or_404(Noise.public_queryset(), pk=noise_id)
    if (
        _noise_year_label(noise) == str(datetime.now().year)
        or not noise.media
        or noise.noise_content_type != 'image'
    ):
        raise Http404

    try:
        noise.media.open('rb')
        with PILImage.open(noise.media) as image:
            image = ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((32, 32), PILImage.Resampling.LANCZOS)
            image = image.filter(ImageFilter.GaussianBlur(radius=5))
            output = BytesIO()
            image.save(output, 'JPEG', quality=32, optimize=True)
    except (OSError, ValueError):
        raise Http404
    finally:
        noise.media.close()

    response = HttpResponse(output.getvalue(), content_type='image/jpeg')
    response['Cache-Control'] = 'public, max-age=604800, immutable'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


