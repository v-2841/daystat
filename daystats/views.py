import datetime
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.db.models import Avg
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
    5: 'май',
    6: 'июнь',
    7: 'июль',
    8: 'август',
    9: 'сентябрь',
    10: 'октябрь',
    11: 'ноябрь',
    12: 'декабрь',
}
PREDICTION_HORIZON = datetime.timedelta(days=365)
SMOOTHING_WINDOWS = {
    '6months': 5,
    'year': 10,
    '5years': 20,
}


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


@login_required
def today(request, date=None):
    if date:
        date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        if date == timezone.localdate():
            return redirect('daystats:today')
        elif date > timezone.localdate():
            context = {
                'date': date,
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
                return redirect('daystats:daystats',
                                date=date.strftime('%Y-%m-%d'))
            return redirect('daystats:today')
        else:
            daystat.refresh_from_db()
    else:
        form = DaystatForm(instance=daystat)

    last_period = Daystat.objects.filter(
        user=request.user,
        period_start=True,
        date__lte=date,
    ).order_by('-date').first()
    if last_period:
        period_day = (date - last_period.date).days + 1
    else:
        period_day = '-'

    context = {
        'date': date,
        'yesterday': date - datetime.timedelta(days=1),
        'tomorrow': (date + datetime.timedelta(days=1)
                     if date != timezone.localdate() else ''),
        'daystat': daystat,
        'form': form,
        'period_day': period_day,
    }
    return render(request, 'daystats/today.html', context)


@login_required
def calendar(request):
    next_period_date = predict_next_period_date(request.user)
    if next_period_date:
        next_period_date_display = next_period_date.strftime('%d.%m.%Y')
        delta_days = (next_period_date - timezone.localdate()).days
        if delta_days > 0:
            next_period_status = f'осталось {delta_days} дн.'
        elif delta_days < 0:
            next_period_status = f'задержка на {abs(delta_days)} дн.'
        else:
            next_period_status = 'сегодня'
    else:
        next_period_date_display = '-'
        next_period_status = '-'

    context = {
        'next_period_date': next_period_date_display,
        'next_period_status': next_period_status,
    }
    return render(request, 'daystats/calendar.html', context)


@login_required
def calendar_api(request):
    data = []
    today = timezone.localdate()
    start = datetime.datetime.fromisoformat(request.GET.get('start')).date()
    end = datetime.datetime.fromisoformat(request.GET.get('end')).date()
    daystats = Daystat.objects.filter(
        user=request.user,
        date__gte=start,
        date__lte=end,
    )
    for daystat in daystats:
        if daystat.period_start:
            data.append({
                'start': daystat.date.strftime('%Y-%m-%d'),
                'title': 'Цикл',
                'backgroundColor': 'rgba(255, 0, 0, 0.2)',
                'borderColor': 'rgba(255, 0, 0, 1)',
            })
        data.append({
            'start': daystat.date.strftime('%Y-%m-%d'),
            'title': f'{daystat.weight if daystat.weight else "-"}',
            'backgroundColor': 'rgba(255, 0, 255, 0.2)',
            'borderColor': 'rgba(255, 0, 255, 1)',
        })
        data.append({
            'start': daystat.date.strftime('%Y-%m-%d'),
            'title': f'{daystat.calories if daystat.calories else "-"}',
            'backgroundColor': 'rgba(0, 0, 255, 0.2)',
            'borderColor': 'rgba(0, 0, 255, 1)',
        })
    for next_period_date in predict_period_dates(
        request.user,
        include_past=True,
    ):
        if not (start <= next_period_date <= end):
            continue
        if next_period_date < today:
            background_color = 'rgba(255, 235, 59, 0.45)'
            border_color = 'rgba(255, 193, 7, 1)'
        else:
            background_color = 'rgba(144, 238, 144, 0.45)'
            border_color = 'rgba(46, 139, 87, 1)'
        data.append({
            'start': next_period_date.strftime('%Y-%m-%d'),
            'title': 'Цикл',
            'backgroundColor': background_color,
            'borderColor': border_color,
        })
    return JsonResponse(data, safe=False)


@login_required
def chart(request):
    return render(request, 'daystats/chart.html')


@login_required
def cycle_weight_chart(request):
    return render(request, 'daystats/cycle_weight_chart.html')


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
def calories_summary(request):
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

    data = defaultdict(lambda: defaultdict(dict))
    for entry in weekly_avg_calories:
        data[entry['year']][entry['week']] = {
            'avg_calories': entry['avg_calories']}
    data = {year: dict(weeks) for year, weeks in data.items()}

    context = {
        'data': data,
    }
    return render(request, 'daystats/calories_summary.html', context)


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
        return redirect('daystats:expenses')
    context = {
        'last_week_expenses': last_week_expenses,
        'form': form,
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


@login_required
def expenses_weeks(request):
    expenses = Expense.objects.filter(user=request.user)
    expenses_list = []
    for expense in expenses:
        local_time = timezone.localtime(expense.created_at)
        expenses_list.append({
            'year': local_time.year,
            'week': int(local_time.strftime('%W')),
            'value': expense.value,
            'note': expense.note,
        })

    grouped_data = defaultdict(lambda: defaultdict(list))
    for expense in expenses_list:
        grouped_data[expense['year']][expense['week']].append(
            {'value': expense['value'], 'note': expense['note']})
    data = {year: dict(weeks) for year, weeks in grouped_data.items()}

    for year, weeks in data.items():
        for week, expenses in weeks.items():
            sum_value = sum(
                [expense['value'] for expense in expenses])
            notes = ', '.join(
                [expense['note'] for expense in expenses if expense['note']])
            data[year][week] = {
                'sum_value': sum_value,
                'notes': notes,
            }

    context = {
        'data': data,
    }
    return render(request, 'daystats/expenses_weeks.html', context)


@login_required
def expenses_months(request):
    expenses = Expense.objects.filter(user=request.user)
    expenses_list = []
    for expense in expenses:
        local_time = timezone.localtime(expense.created_at)
        expenses_list.append({
            'year': local_time.year,
            'month': MONTH_NAMES[local_time.month],
            'value': expense.value,
            'note': expense.note,
        })

    grouped_data = defaultdict(lambda: defaultdict(list))
    for expense in expenses_list:
        grouped_data[expense['year']][expense['month']].append(
            {'value': expense['value'], 'note': expense['note']})
    data = {year: dict(month) for year, month in grouped_data.items()}

    for year, months in data.items():
        for month, expenses in months.items():
            sum_value = sum(
                [expense['value'] for expense in expenses])
            notes = ', '.join(
                [expense['note'] for expense in expenses if expense['note']])
            data[year][month] = {
                'sum_value': sum_value,
                'notes': notes,
            }

    context = {
        'data': data,
    }
    return render(request, 'daystats/expenses_months.html', context)
