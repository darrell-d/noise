import html
import re

import markdown2
from django import template
from django.utils.safestring import mark_safe


register = template.Library()

MARKDOWN_EXTRAS = ["fenced-code-blocks", "tables", "strike", "cuddled-lists", "break-on-newline"]


def _render_markdown(value, inline=False):
    if value is None:
        return ""

    rendered = markdown2.markdown(
        html.escape(str(value)),
        extras=MARKDOWN_EXTRAS,
    )

    if inline:
        rendered = re.sub(r"^<p>(.*)</p>\n?$", r"\1", rendered, flags=re.S)

    return mark_safe(rendered)


@register.filter(name="noise_markdown")
def noise_markdown(value):
    return _render_markdown(value)


@register.filter(name="noise_markdown_inline")
def noise_markdown_inline(value):
    return _render_markdown(value, inline=True)
