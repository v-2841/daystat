import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from daystats.forms import DaystatForm
from daystats.models import Daystat


@login_required
def today(request, date=None):
    if date:
        date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
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

    # День цикла
    last_period = Daystat.objects.filter(
        user=request.user,
        period_start=True,
        date__lt=date,
    ).order_by('-date').first()
    if last_period:
        period_day = (date - last_period.date).days + 1
    else:
        period_day = '-'

    context = {
        'date': date,
        'daystat': daystat,
        'form': form,
        'period_day': period_day,
    }
    return render(request, 'daystats/today.html', context)
