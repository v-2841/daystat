import datetime
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.db.models.functions import ExtractYear
from django.http import JsonResponse
from django.shortcuts import redirect, render

from daystats.forms import DaystatForm
from daystats.models import Daystat


DATE_RANGE = {
    'week': datetime.timedelta(days=7),
    'month': datetime.timedelta(days=30),
    '6months': datetime.timedelta(days=180),
    'year': datetime.timedelta(days=365),
    '5year': datetime.timedelta(days=1825),
}


@login_required
def today(request, date=None):
    if date:
        date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        if date == datetime.date.today():
            return redirect('daystats:today')
        elif date > datetime.date.today():
            context = {
                'date': date,
            }
            return render(request, 'daystats/future_day.html', context)
    else:
        date = datetime.date.today()

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
                     if date != datetime.date.today() else ''),
        'daystat': daystat,
        'form': form,
        'period_day': period_day,
    }
    return render(request, 'daystats/today.html', context)


@login_required
def calendar(request):
    return render(request, 'daystats/calendar.html')


@login_required
def calendar_api(request):
    data = []
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
    return JsonResponse(data, safe=False)


@login_required
def chart(request):
    return render(request, 'daystats/chart.html')


@login_required
def chart_api(request, type, range):
    dataset = {}
    dataset['data'] = []
    today = datetime.date.today()
    start = today - DATE_RANGE[range]
    end = today
    daystats = Daystat.objects.filter(
        user=request.user,
        date__gte=start,
        date__lte=end,
    ).order_by('date')
    if type == 'weight':
        dataset['title'] = 'Вес, кг'
        for daystat in daystats:
            dataset['data'].append(
                [daystat.date.strftime('%Y-%m-%d'), daystat.weight])
    elif type == 'calories':
        dataset['title'] = 'Калории, ккал'
        for daystat in daystats:
            dataset['data'].append(
                [daystat.date.strftime('%Y-%m-%d'), daystat.calories])
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
