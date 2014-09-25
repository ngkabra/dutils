from django import template

register = template.Library()

@register.filter
def django2bootstrap(tags):
    return 'danger' if tags == 'error' else tags

