from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from markdown import markdown

register = template.Library()


@register.filter
def django2bootstrap(tags):
    return 'danger' if tags == 'error' else tags


@register.filter
@stringfilter
def dmarkdown(content):
    '''Markdown without codehilite'''
    return mark_safe(markdown(content))


@register.filter
@stringfilter
def dmarkdownh(content):
    '''Markdown with codehilite'''
    return mark_safe(markdown(
        content,
        extensions=['markdown.extensions.codehilite(guess_lang=False)']))
