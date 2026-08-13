from django.urls import reverse


NAV_ITEMS = (
    ('daystats:home', 'Главная', 'Главная', 'house'),
    ('daystats:day', 'Дневник', 'День', 'notebook'),
    ('daystats:calendar', 'Календарь', 'Календарь', 'calendar-dots'),
    ('daystats:analytics', 'Аналитика', 'Графики', 'chart-line-up'),
    ('daystats:expenses', 'Расходы', 'Расходы', 'wallet'),
)
# url names that should highlight a nav item they do not own
NAV_ALIASES = {
    'daystats:daystats': 'daystats:day',
    'daystats:expenses_weeks': 'daystats:expenses',
    'daystats:expenses_months': 'daystats:expenses',
    'daystats:expense_edit': 'daystats:expenses',
}


def nav(request):
    if not request.user.is_authenticated:
        return {'nav_items': []}

    match = request.resolver_match
    current = match.view_name if match else ''
    current = NAV_ALIASES.get(current, current)

    items = [
        {
            'url': reverse(name),
            'label': label,
            'short': short,
            'icon': icon,
            'active': name == current,
        }
        for name, label, short, icon in NAV_ITEMS
    ]
    return {'nav_items': items}
