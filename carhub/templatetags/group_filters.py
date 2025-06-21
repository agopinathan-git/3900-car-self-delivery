from django import template

register = template.Library()

@register.filter(name='is_in_groups')
def is_in_groups(user, group_names):
    names = [g.strip() for g in group_names.split(',')]
    return user.groups.filter(name__in=names).exists()
