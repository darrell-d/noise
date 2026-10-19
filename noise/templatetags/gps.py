from django import template

from noise.location import FULL, format_location, location_for_user

register = template.Library()


@register.filter(name='gps')
def gps(value):
    return format_location(value, FULL)


@register.simple_tag(takes_context=True)
def noise_location(context, value):
    request = context.get("request")
    return location_for_user(value, getattr(request, "user", None))

register.filter('gps', gps)
