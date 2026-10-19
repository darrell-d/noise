from django.contrib import admin
from django import forms
from django.urls import reverse
from django.utils.html import format_html
from .models import Noise, NoiseVisit


@admin.register(Noise)
class NoiseAdmin(admin.ModelAdmin):
    ordering = Noise.ORDERING
    list_display = (
        'media_preview',
        'admin_title',
        'bucket',
        'noise_content_type',
        'date_added',
        'scrub_exif',
        'video_loop',
        'video_autoplay',
    )
    search_fields = (
        'noise_title',
        'noise_body',
        'noise_extras',
        'noise_url',
        'noise_source',
        'special_guest',
    )
    list_filter = ('noise_content_type', 'bucket', 'scrub_exif', 'video_loop', 'video_autoplay')
    list_per_page = 60
    readonly_fields = ('actual_noise', 'noise_maker', 'body_preview')

    class Media:
        js = ('noise/location-capture.js?v=20260803a',)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'noise_url':
            field.widget = forms.URLInput(attrs={'class': 'vURLField'})
        return field
    fieldsets = (
        ('Content', {
            'fields': (
                'media',
                'noise_title',
                'noise_body',
                'noise_extras',
                'date_added',
                'noise_url',
                'noise_source',
            ),
        }),
        ('Publishing', {
            'fields': (
                'noise_content_type',
                'bucket',
                'location',
                'special_guest',
            ),
        }),
        ('Media behavior', {
            'fields': ('scrub_exif', 'video_loop', 'video_autoplay'),
            'description': 'Image privacy and video playback behavior.',
        }),
        ('System metadata', {
            'fields': ('actual_noise', 'noise_maker', 'body_preview', 'is_tall'),
            'classes': ('collapse',),
            'description': 'Generated values used by the public Noise presentation.',
        }),
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update({
            'title': 'Noise',
            'admin_description': 'Text, media, links and social fragments.',
        })
        return super().changelist_view(request, extra_context=extra_context)

    def admin_title(self, obj):
        return obj.display_title

    @admin.display(description='Media')
    def media_preview(self, obj):
        if not obj.media:
            return ''
        if obj.noise_content_type == 'image':
            return format_html(
                '<img width="112" src="{}" alt="" loading="lazy">',
                reverse('noise-admin-thumbnail', args=[obj.pk]),
            )
        if obj.noise_content_type == 'video':
            return format_html('<span class="material-icons" aria-hidden="true">movie</span>')
        return format_html('<span class="material-icons" aria-hidden="true">attach_file</span>')

    admin_title.short_description = 'Title'


@admin.register(NoiseVisit)
class NoiseVisitAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'user',
        'ip_address',
        'method',
        'status_code',
        'path',
        'noise',
    )
    list_filter = ('method', 'status_code', 'created_at')
    search_fields = ('path', 'user__email', 'user__username', 'ip_address', 'user_agent', 'referrer')
    readonly_fields = (
        'created_at',
        'user',
        'noise',
        'path',
        'method',
        'status_code',
        'ip_address',
        'user_agent',
        'referrer',
    )
    date_hierarchy = 'created_at'
    list_per_page = 100

    def has_add_permission(self, request):
        return False
