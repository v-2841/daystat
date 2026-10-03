import calendar as calendar_module
import datetime
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.http import url_has_allowed_host_and_scheme

from daystats.forms import DaystatForm, ExpenseCategoryForm, ExpenseForm
from daystats.models import Daystat, Expense, ExpenseCategory, alphabetical


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
WEEKDAY_NAMES = ('пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс')
PREDICTION_HORIZON = datetime.timedelta(days=365)
# a gap outside these bounds is a start marked twice or a missed one rather
# than a real cycle, so it is left out of the prediction
CYCLE_DAYS_MIN = 15
CYCLE_DAYS_MAX = 60
SMOOTHING_WINDOWS = {
    '6months': 5,
    'year': 10,
    '5years': 20,
}


def format_date(date):
    return date_format(date, 'j E Y')


def current_week_start():
    """Midnight of the Monday of the current week, in the local timezone."""
    today = timezone.localdate()
    monday = today - datetime.timedelta(days=today.weekday())
    return timezone.make_aware(
        datetime.datetime.combine(monday, datetime.time.min),
    )


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


def predict_next_period_date(user, predicted_dates=None):
    today = timezone.localdate()
    if predicted_dates is None:
        predicted_dates = predict_period_dates(user, include_past=True)
    overdue_dates = [date for date in predicted_dates if date < today]
    if overdue_dates:
        # the first missed date, so the delay keeps growing instead of
        # resetting on every skipped prediction
        return overdue_dates[0]

    for predicted_date in predicted_dates:
        if predicted_date >= today:
            return predicted_date
    return None


def predict_period_dates(user, include_past=False):
    if not user.tracks_cycle:
        return []
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
        dates_diff = [diff for diff in dates_diff
                      if CYCLE_DAYS_MIN <= diff <= CYCLE_DAYS_MAX]
        if not dates_diff:
            return []
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
    if not user.tracks_cycle:
        return None
    last_period = Daystat.objects.filter(
        user=user,
        period_start=True,
        date__lte=date,
    ).order_by('-date').first()
    if last_period:
        return (date - last_period.date).days + 1
    return None


def get_next_period_summary(user, predicted_dates=None):
    next_period_date = predict_next_period_date(user, predicted_dates)
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
    week_expenses = Expense.objects.filter(
        user=user,
        created_at__gte=current_week_start(),
    ).aggregate(total=Sum('value'))['total'] or 0

    context = {
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
        try:
            date = datetime.date.fromisoformat(date)
        except ValueError:
            raise Http404('Некорректная дата')
        # the neighbour days are computed below, so the edges of the
        # calendar have to stay reachable
        if not datetime.date.min < date < datetime.date.max:
            raise Http404('Дата вне допустимого диапазона')
        # a form left open past midnight posts here to its own day
        if date == timezone.localdate() and request.method != 'POST':
            return redirect('daystats:day')
        elif date > timezone.localdate():
            context = {
                'date': date,
                'date_display': format_date(date),
            }
            return render(request, 'daystats/future_day.html', context)
    else:
        date = timezone.localdate()
    daystat = Daystat.objects.filter(user=request.user, date=date).first()

    if request.method == 'POST':
        # the row is created only when there is something to save
        if daystat is None:
            daystat = Daystat(user=request.user, date=date)
        form = DaystatForm(request.POST, instance=daystat,
                           tracks_cycle=request.user.tracks_cycle)
        if form.is_valid():
            form.save()
            url = (reverse('daystats:day') if date == timezone.localdate()
                   else reverse('daystats:daystats', args=[date.isoformat()]))
            return redirect(f'{url}?saved=1')
    else:
        form = DaystatForm(instance=daystat,
                           tracks_cycle=request.user.tracks_cycle)

    is_today = date == timezone.localdate()
    context = {
        'date': date,
        'date_display': format_date(date),
        'is_today': is_today,
        'yesterday': date - datetime.timedelta(days=1),
        'tomorrow': (date + datetime.timedelta(days=1)
                     if not is_today else None),
        'form': form,
        'period_day': get_period_day(request.user, date),
        'saved': request.GET.get('saved') == '1',
    }
    return render(request, 'daystats/day.html', context)


@login_required
def calendar(request):
    today_date = timezone.localdate()
    year, month = today_date.year, today_date.month
    requested = request.GET.get('month', '')
    if requested:
        try:
            parts = [int(part) for part in requested.split('-')]
            if len(parts) != 2:
                raise ValueError('ожидается ГГГГ-ММ')
            # a week of padding on both sides has to stay a valid date
            probe_year, probe_month = parts
            first = datetime.date(probe_year, probe_month, 1)
            last = datetime.date(
                probe_year, probe_month,
                calendar_module.monthrange(probe_year, probe_month)[1],
            )
            first - datetime.timedelta(days=7)
            last + datetime.timedelta(days=7)
        except (ValueError, TypeError, OverflowError):
            pass
        else:
            year, month = probe_year, probe_month

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
    predicted_dates = predict_period_dates(request.user, include_past=True)
    predicted = {
        date for date in predicted_dates
        if grid_start <= date <= grid_end
    }

    tracks_cycle = request.user.tracks_cycle
    weeks = []
    for row in grid:
        week = []
        for date in row:
            daystat = daystats.get(date)
            week.append({
                'date': date,
                'day': date.day,
                'in_month': date.month == month,
                'is_today': date == today_date,
                'is_future': date > today_date,
                'weight': daystat.weight if daystat else None,
                'calories': daystat.calories if daystat else None,
                'period_start': bool(tracks_cycle and daystat
                                     and daystat.period_start),
                'predicted': date in predicted and not (
                    daystat and daystat.period_start
                ),
                'predicted_overdue': date in predicted and date < today_date,
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
        'is_current_month': (year, month) == (today_date.year,
                                              today_date.month),
        'next_period': get_next_period_summary(
            request.user, predicted_dates=predicted_dates,
        ),
        'avg_weight': month_stats['avg_weight'],
        'avg_calories': month_stats['avg_calories'],
    }
    return render(request, 'daystats/calendar.html', context)


@login_required
def analytics(request):
    tab = request.GET.get('tab', 'trends')
    if tab not in ('trends', 'cycle', 'weeks'):
        tab = 'trends'
    if tab == 'cycle' and not request.user.tracks_cycle:
        tab = 'trends'

    context = {'tab': tab}
    if tab == 'weeks':
        daystats = (
            Daystat.objects
            .filter(user=request.user, calories__gt=0)
            .values_list('date', 'calories')
        )

        # grouped by ISO year and week, so a week spanning the new year
        # stays one row instead of splitting into «week 52» and «week 0»
        buckets = defaultdict(list)
        for date, calories in daystats:
            iso = date.isocalendar()
            buckets[(iso.year, iso.week)].append(calories)

        data = defaultdict(dict)
        for (year, week) in sorted(buckets, reverse=True):
            values = buckets[(year, week)]
            data[year][week] = {
                'avg_calories': sum(values) / len(values),
            }
        context['data'] = dict(data)
    return render(request, 'daystats/analytics.html', context)


@login_required
def chart_api(request, type, range):
    if range not in DATE_RANGE or type not in ('weight', 'calories'):
        raise Http404('Неизвестный график')

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
    if not request.user.tracks_cycle:
        raise Http404('Цикл не отслеживается')
    daystats = list(
        Daystat.objects.filter(
            user=request.user,
        ).order_by('date')
    )

    weighed = [daystat for daystat in daystats if daystat.weight is not None]
    if weighed:
        range_name = get_range_name_for_dates(
            weighed[0].date,
            weighed[-1].date,
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
    week_expenses = Expense.objects.filter(
        user=request.user,
        created_at__gte=current_week_start(),
    ).select_related('category').order_by('-created_at')
    form = ExpenseForm(request.POST or None,
                       instance=Expense(user=request.user))
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect(f'{request.path}?saved=1')
    context = {
        'week_expenses': week_expenses,
        'week_total': sum(
            expense.value for expense in week_expenses
        ),
        'form': form,
        'tab': 'list',
        'saved': request.GET.get('saved') == '1',
    }
    return render(request, 'daystats/expenses.html', context)


@login_required
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    # only a real path is accepted: a view name here would blow up in reverse()
    next_page = request.GET.get('next', '')
    if not next_page.startswith('/') or not url_has_allowed_host_and_scheme(
        url=next_page,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_page = reverse('daystats:expenses')
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
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        expense.delete()
    return redirect('daystats:expenses')


@login_required
def expense_categories(request):
    categories = sorted(
        ExpenseCategory.objects.filter(user=request.user).annotate(
            count=Count('expenses'),
            total=Sum('expenses__value'),
        ),
        key=lambda category: alphabetical(category.name),
    )
    form = ExpenseCategoryForm(request.POST or None,
                               instance=ExpenseCategory(user=request.user))
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('daystats:expense_categories')
    context = {
        'categories': categories,
        'form': form,
        'tab': 'categories',
    }
    return render(request, 'daystats/expense_categories.html', context)


@login_required
def expense_category_edit(request, pk):
    category = get_object_or_404(ExpenseCategory, pk=pk, user=request.user)
    form = ExpenseCategoryForm(request.POST or None, instance=category)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('daystats:expense_categories')
    context = {
        'form': form,
        'category': category,
    }
    return render(request, 'daystats/expense_category_edit.html', context)


@login_required
def expense_category_delete(request, pk):
    category = get_object_or_404(ExpenseCategory, pk=pk, user=request.user)
    # the expenses stay, only without the category
    if request.method == 'POST':
        category.delete()
    return redirect('daystats:expense_categories')


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
            totals = defaultdict(int)
            for item in items:
                totals[item.category] += item.value
            # a period recorded before the categories needs no breakdown
            categories = []
            if any(totals):
                categories = sorted(totals.items(),
                                    key=lambda pair: pair[1], reverse=True)
            data[year][key] = {
                'sum_value': sum(item.value for item in items),
                'notes': notes,
                'categories': categories,
                'label': label_func(key),
            }
    return data


@login_required
def expenses_weeks(request):
    expenses = Expense.objects.filter(
        user=request.user,
    ).select_related('category')
    context = {
        'data': group_expenses(
            expenses,
            lambda dt: dt.isocalendar()[:2],
            lambda week: f'Неделя {week}',
        ),
        'tab': 'weeks',
        'unit_label': 'Неделя',
    }
    return render(request, 'daystats/expenses_summary.html', context)


@login_required
def expenses_months(request):
    expenses = Expense.objects.filter(
        user=request.user,
    ).select_related('category')
    context = {
        'data': group_expenses(
            expenses,
            lambda dt: (dt.year, dt.month),
            lambda month: MONTH_NAMES[month].capitalize(),
        ),
        'tab': 'months',
        'unit_label': 'Месяц',
    }
    return render(request, 'daystats/expenses_summary.html', context)
