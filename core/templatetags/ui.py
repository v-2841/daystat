from django import template
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import mark_safe


register = template.Library()


@register.simple_tag
def icon(name, classes='icon'):
    """Render a Phosphor duotone icon from the static SVG sprite."""
    return format_html(
        '<svg class="{}" aria-hidden="true" focusable="false">'
        '<use href="{}#ph-{}"></use></svg>',
        classes,
        static('img/sprite.svg'),
        name,
    )


@register.filter
def field_class(field, css):
    """Add CSS classes to a form field widget, keeping existing attrs."""
    attrs = dict(field.field.widget.attrs)
    existing = attrs.pop('class', '')
    attrs['class'] = f'{existing} {css}'.strip()
    return field.as_widget(attrs=attrs)


@register.filter
def money(value):
    """Format an integer amount with thin non-breaking space separators."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    return mark_safe(f'{value:,}'.replace(',', '&#8239;'))
