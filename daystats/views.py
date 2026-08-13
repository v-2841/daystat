import calendar as calendar_module
import datetime
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum
from django.db.models.functions import ExtractYear
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from daystats.forms import DaystatForm, ExpenseForm
from daystats.models import Daystat, Expense


DATE_RANGE = {
    'week': datetime.timedelta(days=7),
    'month': datetime.timedelta(days=30),
    '6months': datetime.timedelta(days=180),
    'year': datetime.timedelta(days=365),
    '5years': datetime.timedelta(days=1825),
}
MONTH_NAMES = {
    1: 'январь',
    2: 'февраль',
    3: 'март',
    4: 'апрель',
    5: 'май',
    6: 'июнь',
    7: 'июль',
    8: 'август',
    9: 'сентябрь',
    10: 'октябрь',
    11: 'ноябрь',
    12: 'декабрь',
}
MONTH_NAMES_GENITIVE = {
    1: 'января',
    2: 'февраля',
    3: 'марта',
    4: 'апреля',
    5: 'мая',
    6: 'июня',
    7: 'июля',
    8: 'августа',
    9: 'сентября',
    10: 'октября',
    11: 'ноября',
    12: 'декабря',
}
WEEKDAY_NAMES = ('пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс')
PREDICTION_HORIZON = datetime.timedelta(days=365)
SMOOTHING_WINDOWS = {
    '6months': 5,
    'year': 10,
    '5years': 20,
}


def format_date(date):
    return f'{date.day} {MONTH_NAMES_GENITIVE[date.month]} {date.year}'


def moving_average(points, window_size):
    if window_size <= 1 or not points:
        return points

    half_window = window_size // 2
    smoothed_points = []
    for index, (point_date, _) in enumerate(points):
        start = max(0, index - half_window)
        end = min(len(points), index + half_window + 1)
        window_values = [value for _, value in points[start:end]]
        average = round(sum(window_values) / len(window_values), 2)
        smoothed_points.append((point_date, average))
    return smoothed_points


def build_chart_points(daystats, field_name, range_name):
    points = []
    for daystat in daystats:
        value = getattr(daystat, field_name)
        if value is None:
            continue
        points.append((daystat.date, value))

    window_size = SMOOTHING_WINDOWS.get(range_name)
    if window_size:
        points = moving_average(points, window_size)

    return [[point_date.strftime('%Y-%m-%d'), value]
            for point_date, value in points]


def get_range_name_for_dates(start_date, end_date):
    if not start_date or not end_date:
        return 'week'

    date_range = end_date - start_date
    if date_range <= DATE_RANGE['week']:
        return 'week'
    if date_range <= DATE_RANGE['month']:
        return 'month'
    if date_range <= DATE_RANGE['6months']:
        return '6months'
    if date_range <= DATE_RANGE['year']:
        return 'year'
    return '5years'


def build_cycle_length_points(daystats):
    points = []
    period_starts = [
        daystat.date for daystat in daystats if daystat.period_start
    ]
    for start_date, next_start_date in zip(period_starts, period_starts[1:]):
        cycle_length = (next_start_date - start_date).days
        points.append([next_start_date.strftime('%Y-%m-%d'), cycle_length])
    return points


def predict_next_period_date(user):
    today = timezone.localdate()
    predicted_dates = predict_period_dates(user, include_past=True)
    overdue_dates = [date for date in predicted_dates if date < today]
    if overdue_dates:
        return overdue_dates[-1]

    for predicted_date in predicted_dates:
        if predicted_date >= today:
            return predicted_date
    return None


def predict_period_dates(user, include_past=False):
    periods_days = list(
        Daystat.objects.filter(
            user=user,
            date__gte=timezone.localdate() - DATE_RANGE['year'],
            period_start=True,
        )
        .values_list('date', flat=True)
        .order_by('-date')
    )
    if len(periods_days) > 1:
        dates = periods_days
        dates_diff = [(dates[i] - dates[i + 1]).days
                      for i in range(len(dates) - 1)]
        weights = list(range(len(dates_diff), 0, -1))
        next_period_diff = (sum(d * w for d, w in zip(dates_diff, weights))
                            / sum(weights))
        cycle_days = round(next_period_diff)
        last_period_date = dates[0]
        today = timezone.localdate()
        horizon_end = today + PREDICTION_HORIZON

        predicted_dates = []
        predicted_date = last_period_date + datetime.timedelta(days=cycle_days)
        while predicted_date <= horizon_end:
            if include_past or predicted_date >= today:
                predicted_dates.append(predicted_date)
            predicted_date += datetime.timedelta(days=cycle_days)
        return predicted_dates
    return []


def get_period_day(user, date):
    last_period = Daystat.objects.filter(
        user=user,
        period_start=True,
        date__lte=date,
    ).order_by('-date').first()
    if last_period:
        return (date - last_period.date).days + 1
    return None


def get_next_period_summary(user):
    next_period_date = predict_next_period_date(user)
    if not next_period_date:
        return {'date': None, 'status': 'нет данных', 'tone': 'muted'}

    delta_days = (next_period_date - timezone.localdate()).days
    if delta_days > 0:
        status = f'через {delta_days} дн.'
        tone = 'upcoming'
    elif delta_days < 0:
        status = f'задержка {abs(delta_days)} дн.'
        tone = 'overdue'
    else:
        status = 'сегодня'
        tone = 'today'
    return {'date': next_period_date, 'status': status, 'tone': tone}


@login_required
def home(request):
    user = request.user
    today_date = timezone.localdate()
    daystat = Daystat.objects.filter(user=user, date=today_date).first()
    week_start = today_date - datetime.timedelta(days=today_date.weekday())
    week_expenses = Expense.objects.filter(
        user=user,
        created_at__gte=timezone.make_aware(
            datetime.datetime.combine(week_start, datetime.time.min),
        ),
    ).aggregate(total=Sum('value'))['total'] or 0

    context = {
        'today_date': today_date,
        'today_display': format_date(today_date),
        'daystat': daystat,
        'period_day': get_period_day(user, today_date),
        'next_period': get_next_period_summary(user),
        'week_expenses': week_expenses,
    }
    return render(request, 'daystats/home.html', context)


@login_required
def day(request, date=None):
    if date:
        date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        if date == timezone.localdate():
            return redirect('daystats:day')
        elif date > timezone.localdate():
            context = {
                'date': date,
                'date_display': format_date(date),
            }
            return render(request, 'daystats/future_day.html', context)
    else:
        date = timezone.localdate()
    daystat, _ = Daystat.objects.get_or_create(
        user=request.user,
        date=date,
    )

    if request.method == 'POST':
        form = DaystatForm(request.POST, instance=daystat)
        if form.is_valid():
            form.save()
            if request.resolver_match.view_name == 'daystats:daystats':
                return redirect(
                    f'{request.path}?saved=1',
                )
            return redirect(f"{request.path}?saved=1")
        else:
            daystat.refresh_from_db()
    else:
        form = DaystatForm(instance=daystat)

    is_today = date == timezone.localdate()
    context = {
        'date': date,
        'date_display': format_date(date),
        'is_today': is_today,
        'yesterday': date - datetime.timedelta(days=1),
        'tomorrow': (date + datetime.timedelta(days=1)
                     if not is_today else None),
        'daystat': daystat,
        'form': form,
        'period_day': get_period_day(request.user, date),
        'saved': request.GET.get('saved') == '1',
    }
    return render(request, 'daystats/day.html', context)


@login_required
def calendar(request):
    today_date = timezone.localdate()
    try:
        year, month = (int(part)
                       for part in request.GET.get('month', '').split('-'))
        datetime.date(year, month, 1)
    except (ValueError, TypeError):
        year, month = today_date.year, today_date.month

    first_day = datetime.date(year, month, 1)
    last_day = datetime.date(
        year, month, calendar_module.monthrange(year, month)[1],
    )
    grid = calendar_module.Calendar(firstweekday=0).monthdatescalendar(
        year, month,
    )
    grid_start, grid_end = grid[0][0], grid[-1][-1]

    daystats = {
        daystat.date: daystat
        for daystat in Daystat.objects.filter(
            user=request.user,
            date__gte=grid_start,
            date__lte=grid_end,
        )
    }
    predicted = {
        date for date in predict_period_dates(request.user, include_past=True)
        if grid_start <= date <= grid_end
    }

    weeks = []
    for row in grid:
        week = []
        for date in row:
            daystat = daystats.get(date)
            has_data = bool(
                daystat and (daystat.weight or daystat.calories
                             or daystat.period_start)
            )
            week.append({
                'date': date,
                'day': date.day,
                'in_month': date.month == month,
                'is_today': date == today_date,
                'is_future': date > today_date,
                'weight': daystat.weight if daystat else None,
                'calories': daystat.calories if daystat else None,
                'period_start': bool(daystat and daystat.period_start),
                'predicted': date in predicted and not (
                    daystat and daystat.period_start
                ),
                'predicted_overdue': date in predicted and date < today_date,
                'has_data': has_data,
                'display': format_date(date),
            })
        weeks.append(week)

    prev_month = (first_day - datetime.timedelta(days=1)).strftime('%Y-%m')
    next_month = (last_day + datetime.timedelta(days=1)).strftime('%Y-%m')

    month_stats = Daystat.objects.filter(
        user=request.user,
        date__gte=first_day,
        date__lte=last_day,
    ).aggregate(avg_weight=Avg('weight'), avg_calories=Avg('calories'))

    context = {
        'weeks': weeks,
        'weekday_names': WEEKDAY_NAMES,
        'month_title': f'{MONTH_NAMES[month].capitalize()} {year}',
        'prev_month': prev_month,
        'next_month': next_month,
        'current_month': f'{year:04d}-{month:02d}',
        'is_current_month': (year, month) == (today_date.year,
                                              today_date.month),
        'next_period': get_next_period_summary(request.user),
        'period_day': get_period_day(request.user, today_date),
        'avg_weight': month_stats['avg_weight'],
        'avg_calories': month_stats['avg_calories'],
    }
    return render(request, 'daystats/calendar.html', context)


@login_required
def analytics(request):
    tab = request.GET.get('tab', 'trends')
    if tab not in ('trends', 'cycle', 'weeks'):
        tab = 'trends'

    context = {'tab': tab}
    if tab == 'weeks':
        weekly_avg_calories = (
            Daystat.objects
            .filter(
                user=request.user,
                calories__gt=0,
            )
            .annotate(
                year=ExtractYear('date'),
            )
            .values('year', 'week')
            .annotate(avg_calories=Avg('calories'))
            .order_by('-year', '-week')
        )

        data = defaultdict(dict)
        for entry in weekly_avg_calories:
            data[entry['year']][entry['week']] = {
                'avg_calories': entry['avg_calories'],
            }
        context['data'] = {year: weeks for year, weeks in data.items()}
    return render(request, 'daystats/analytics.html', context)


@login_required
def chart_api(request, type, range):
    dataset = {}
    dataset['data'] = []
    today = timezone.localdate()
    start = today - DATE_RANGE[range]
    end = today
    daystats = Daystat.objects.filter(
        user=request.user,
        date__gte=start,
        date__lte=end,
    ).order_by('date')
    if type == 'weight':
        dataset['title'] = 'Вес, кг'
        dataset['data'] = build_chart_points(daystats, 'weight', range)
    elif type == 'calories':
        dataset['title'] = 'Калории, ккал'
        dataset['data'] = build_chart_points(daystats, 'calories', range)
    return JsonResponse(dataset)


@login_required
def cycle_weight_chart_api(request):
    daystats = list(
        Daystat.objects.filter(
            user=request.user,
        ).order_by('date')
    )

    if daystats:
        range_name = get_range_name_for_dates(
            daystats[0].date,
            daystats[-1].date,
        )
    else:
        range_name = 'week'

    dataset = {
        'datasets': [
            {
                'data': build_cycle_length_points(daystats),
            },
            {
                'data': build_chart_points(daystats, 'weight', range_name),
            },
        ],
    }
    return JsonResponse(dataset)


@login_required
def expenses(request):
    last_week_expenses = Expense.objects.filter(
        user=request.user,
        created_at__gte=timezone.now() - DATE_RANGE['week'],
    ).order_by('-created_at')
    form = ExpenseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        expense = form.save(commit=False)
        expense.user = request.user
        expense.save()
        return redirect(f"{request.path}?saved=1")
    context = {
        'last_week_expenses': last_week_expenses,
        'week_total': sum(
            expense.value for expense in last_week_expenses
        ),
        'form': form,
        'tab': 'list',
        'saved': request.GET.get('saved') == '1',
    }
    return render(request, 'daystats/expenses.html', context)


@login_required
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.user != expense.user:
        return redirect('daystats:expenses')
    next_page = request.GET.get('next', 'daystats:expenses')
    if not url_has_allowed_host_and_scheme(
        url=next_page,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_page = 'daystats:expenses'
    form = ExpenseForm(request.POST or None, instance=expense)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect(next_page)
    context = {
        'form': form,
        'expense': expense,
    }
    return render(request, 'daystats/expense_edit.html', context)


@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.user == expense.user and request.method == 'POST':
        expense.delete()
    return redirect('daystats:expenses')


def group_expenses(expenses, key_func, label_func):
    grouped = defaultdict(lambda: defaultdict(list))
    for expense in expenses:
        local_time = timezone.localtime(expense.created_at)
        year, key = key_func(local_time)
        grouped[year][key].append(expense)

    data = {}
    for year, groups in grouped.items():
        data[year] = {}
        for key, items in groups.items():
            notes = ', '.join(item.note for item in items if item.note)
            data[year][key] = {
                'sum_value': sum(item.value for item in items),
                'notes': notes,
                'count': len(items),
                'label': label_func(key),
            }
    return data


@login_required
def expenses_weeks(request):
    expenses = Expense.objects.filter(user=request.user)
    context = {
        'data': group_expenses(
            expenses,
            lambda dt: (dt.year, int(dt.strftime('%W'))),
            lambda week: f'Неделя {week}',
        ),
        'tab': 'weeks',
        'unit_label': 'Неделя',
    }
    return render(request, 'daystats/expenses_summary.html', context)


@login_required
def expenses_months(request):
    expenses = Expense.objects.filter(user=request.user)
    context = {
        'data': group_expenses(
            expenses,
            lambda dt: (dt.year, MONTH_NAMES[dt.month]),
            lambda month: month.capitalize(),
        ),
        'tab': 'months',
        'unit_label': 'Месяц',
    }
    return render(request, 'daystats/expenses_summary.html', context)
