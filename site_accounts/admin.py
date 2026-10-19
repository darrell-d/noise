from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import UserIdentity


class UserIdentityInline(admin.TabularInline):
    model = UserIdentity
    extra = 0
    fields = ("kind", "identifier", "is_verified")


User = get_user_model()
admin.site.unregister(User)


@admin.register(User)
class SiteUserAdmin(DjangoUserAdmin):
    inlines = (UserIdentityInline,)


@admin.register(UserIdentity)
class UserIdentityAdmin(admin.ModelAdmin):
    list_display = ("identifier", "kind", "user", "is_verified", "updated_at")
    list_filter = ("kind", "is_verified")
    search_fields = ("identifier", "user__username", "user__email")
    autocomplete_fields = ("user",)
    ordering = ("user__email", "kind", "identifier")
