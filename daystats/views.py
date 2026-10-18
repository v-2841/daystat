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
UNCATEGORIZED = 'Без категории'
SMOOTHING_WINDOWS = {
    '6months': 5,
    'year': 10,
    '5years': 20,
}
# how many highs and how many lows the chart marks on each range
KEY_POINT_COUNTS = {
    'week': 1,
    'month': 2,
    '6months': 3,
    'year': 4,
    '5years': 5,
}


def format_date(date):
    return date_format(date, 'j E Y')


def local_midnight(date):
    return timezone.make_aware(
        datetime.datetime.combine(date, datetime.time.min),
    )


def current_week_start():
    """Midnight of the Monday of the current week, in the local timezone."""
    today = timezone.localdate()
    return local_midnight(today - datetime.timedelta(days=today.weekday()))


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


def collect_points(daystats, field_name):
    points = []
    for daystat in daystats:
        value = getattr(daystat, field_name)
        if value is None:
            continue
        points.append((daystat.date, value))
    return points


def format_points(points):
    return [[point_date.strftime('%Y-%m-%d'), value]
            for point_date, value in points]


def build_chart_points(points, range_name):
    window_size = SMOOTHING_WINDOWS.get(range_name)
    if window_size:
        points = moving_average(points, window_size)
    return format_points(points)


def peak_prominences(values):
    """How far every local maximum rises above the deepest dip that
    separates it from a higher value, by index.

    A side that runs into the edge of the period without a higher value
    is left out: the period cuts the hill there, it is not a dip. The
    highest value has neither side and is measured from the lowest one,
    so it always ranks first.
    """
    lowest = min(values)
    prominences = {}
    for index, value in enumerate(values):
        if index > 0 and values[index - 1] >= value:
            continue
        if index < len(values) - 1 and values[index + 1] > value:
            continue
        dips = []
        for step in (-1, 1):
            dip = value
            position = index + step
            while 0 <= position < len(values) and values[position] <= value:
                dip = min(dip, values[position])
                position += step
            if 0 <= position < len(values):
                dips.append(dip)
        prominences[index] = value - max(dips, default=lowest)
    return prominences


def pick_peaks(points, values, count):
    """The `count` most prominent peaks of values, kept 1/(2 * count) of
    the period apart so that they mark different stretches of it."""
    min_gap = (points[-1][0] - points[0][0]) / (2 * count)
    prominences = peak_prominences(values)
    picked = []
    for index in sorted(prominences, key=prominences.get, reverse=True):
        if len(picked) == count or prominences[index] <= 0:
            break
        if all(abs(points[index][0] - points[other][0]) >= min_gap
               for other in picked):
            picked.append(index)
    return format_points(points[index] for index in sorted(picked))


def build_key_points(points, range_name):
    """The real highs and lows of the period that the chart labels:
    the smoothed line flattens them on the longer ranges."""
    values = [value for _, value in points]
    if not values or min(values) == max(values):
        return [], []
    count = KEY_POINT_COUNTS[range_name]
    highs = pick_peaks(points, values, count)
    lows = pick_peaks(points, [-value for value in values], count)
    return highs, lows


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
        excluded_from_week=False,
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
    elif type == 'calories':
        dataset['title'] = 'Калории, ккал'
    points = collect_points(daystats, type)
    dataset['data'] = build_chart_points(points, range)
    dataset['highs'], dataset['lows'] = build_key_points(points, range)
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

    weights = collect_points(daystats, 'weight')
    if weights:
        range_name = get_range_name_for_dates(
            weights[0][0],
            weights[-1][0],
        )
    else:
        range_name = 'week'

    dataset = {
        'datasets': [
            {
                'data': build_cycle_length_points(daystats),
            },
            {
                'data': build_chart_points(weights, range_name),
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
        # an excluded expense stays in the list, marked, but not in the total
        'week_total': sum(
            expense.value for expense in week_expenses
            if not expense.excluded_from_week
        ),
        'form': form,
        'tab': 'list',
        'saved': request.GET.get('saved') == '1',
    }
    return render(request, 'daystats/expenses.html', context)


def get_next_page(request):
    """The page an expense form returns to: the list it was opened from."""
    # only a real path is accepted: a view name here would blow up in reverse()
    next_page = request.GET.get('next', '')
    if not next_page.startswith('/') or not url_has_allowed_host_and_scheme(
        url=next_page,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_page = reverse('daystats:expenses')
    return next_page


@login_required
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    next_page = get_next_page(request)
    form = ExpenseForm(request.POST or None, instance=expense)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect(next_page)
    context = {
        'form': form,
        'expense': expense,
        'next_page': next_page,
    }
    return render(request, 'daystats/expense_edit.html', context)


@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        expense.delete()
    return redirect(get_next_page(request))


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


def breakdown_line(expense):
    """The line of a summary breakdown an expense counts towards: its
    category, or else its note, which is how the expenses recorded before
    the categories tell what they were for."""
    if expense.category:
        return expense.category.name
    if expense.note and expense.note.strip():
        return expense.note.strip()
    return UNCATEGORIZED


def build_breakdown(items):
    totals = {}
    for item in items:
        line = breakdown_line(item)
        # a note «такси» joins the category «Такси», shown as the category
        key = alphabetical(line)
        name, total = totals.get(key, (line, 0))
        if item.category:
            name = line
        totals[key] = (name, total + item.value)
    # a period of bare amounts needs no breakdown
    if set(totals) == {alphabetical(UNCATEGORIZED)}:
        return []
    return sorted(totals.values(), key=lambda pair: pair[1], reverse=True)


def group_expenses(expenses, key_func, label_func, url_name):
    grouped = defaultdict(lambda: defaultdict(list))
    for expense in expenses:
        local_time = timezone.localtime(expense.created_at)
        year, key = key_func(local_time)
        grouped[year][key].append(expense)

    data = {}
    for year, groups in grouped.items():
        data[year] = {}
        for key, items in groups.items():
            data[year][key] = {
                'sum_value': sum(item.value for item in items),
                'categories': build_breakdown(items),
                'label': label_func(key),
                # the page with every expense of the period, to fix one
                'url': reverse(url_name, args=(year, key)),
            }
    return data


@login_required
def expenses_weeks(request):
    expenses = Expense.objects.filter(
        user=request.user,
        excluded_from_week=False,
    ).select_related('category')
    context = {
        'data': group_expenses(
            expenses,
            lambda dt: dt.isocalendar()[:2],
            lambda week: f'Неделя {week}',
            'daystats:expenses_week',
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
            'daystats:expenses_month',
        ),
        'tab': 'months',
        'unit_label': 'Месяц',
    }
    return render(request, 'daystats/expenses_summary.html', context)


def period_expenses(user, first_day, end_day):
    """The expenses from first_day up to, but not including, end_day."""
    return Expense.objects.filter(
        user=user,
        created_at__gte=local_midnight(first_day),
        created_at__lt=local_midnight(end_day),
    ).select_related('category')


@login_required
def expenses_week(request, year, week):
    try:
        monday = datetime.date.fromisocalendar(year, week, 1)
        next_monday = monday + datetime.timedelta(days=7)
    except (ValueError, OverflowError):
        raise Http404('Нет такой недели')
    sunday = next_monday - datetime.timedelta(days=1)
    if monday.month == sunday.month:
        dates = f'{monday.day}–{format_date(sunday)}'
    else:
        first_format = 'j E' if monday.year == sunday.year else 'j E Y'
        dates = f'{date_format(monday, first_format)} – {format_date(sunday)}'
    expenses = period_expenses(request.user, monday, next_monday)
    context = {
        'title': f'Неделя {week}',
        'dates': dates,
        'expenses': expenses,
        # the same total as the weekly summary shows
        'total': sum(
            expense.value for expense in expenses
            if not expense.excluded_from_week
        ),
        'tab': 'weeks',
    }
    return render(request, 'daystats/expenses_period.html', context)


@login_required
def expenses_month(request, year, month):
    try:
        first_day = datetime.date(year, month, 1)
        # 31 days from the 1st always land in the next month
        end_day = (first_day + datetime.timedelta(days=31)).replace(day=1)
    except (ValueError, OverflowError):
        raise Http404('Нет такого месяца')
    expenses = period_expenses(request.user, first_day, end_day)
    context = {
        'title': f'{MONTH_NAMES[month].capitalize()} {year}',
        'expenses': expenses,
        'total': sum(expense.value for expense in expenses),
        'tab': 'months',
    }
    return render(request, 'daystats/expenses_period.html', context)
