from django.db import migrations


def to_iso_weeks(apps, schema_editor):
    Daystat = apps.get_model('daystats', 'Daystat')
    updated = []
    for daystat in Daystat.objects.all().only('id', 'date', 'week'):
        week = daystat.date.isocalendar().week
        if daystat.week != week:
            daystat.week = week
            updated.append(daystat)
    Daystat.objects.bulk_update(updated, ['week'], batch_size=500)


def to_strftime_weeks(apps, schema_editor):
    Daystat = apps.get_model('daystats', 'Daystat')
    updated = []
    for daystat in Daystat.objects.all().only('id', 'date', 'week'):
        week = int(daystat.date.strftime('%W'))
        if daystat.week != week:
            daystat.week = week
            updated.append(daystat)
    Daystat.objects.bulk_update(updated, ['week'], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('daystats', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(to_iso_weeks, to_strftime_weeks),
    ]
