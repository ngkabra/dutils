from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from markdown import markdown
import random

register = template.Library()


@register.filter
@stringfilter
def random_choice(choices):
    '''Randomly choose one of the choices and return it

    Choices is a comma separated string (for now)'''
    return random.choice([c.strip() for c in choices.split(',')])


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
    return mark_safe(markdown(content,
                              extensions=['codehilite(guess_lang=False)']))


@register.filter
@stringfilter
def chop_markdown(content):
    content = content.strip()
    if content[:3].lower() == '<p>' and content[-4:] == '</p>':
        content = content[3:-4]
    return mark_safe(content)
