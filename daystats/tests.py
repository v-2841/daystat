import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from daystats.forms import DaystatForm
from daystats.models import Daystat


class DaystatTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser', password='password')
        self.client.login(username='testuser', password='password')
        self.date = datetime.date.today()
        self.daystat = Daystat.objects.create(
            user=self.user,
            date=self.date,
            calories=2000,
            weight=70.5,
            period_start=True,
        )

    def test_today_view(self):
        """Доступ к вьюхе 'today' для авторизованного пользователя"""
        response = self.client.get(reverse('daystats:today'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'daystats/today.html')
        self.assertContains(response, '2000')
        self.assertContains(response, '70.5')
        self.assertContains(response, 'undavg')  # Цикл начался

    def test_daystat_creation(self):
        """Корректное создание объекта Daystat с заданными данными"""
        self.assertEqual(Daystat.objects.count(), 1)
        self.assertEqual(self.daystat.calories, 2000)
        self.assertEqual(self.daystat.weight, 70.5)

    def test_daystat_unique_constraint(self):
        """Пользователь не может иметь более одной записи Daystat за день"""
        with self.assertRaises(Exception):
            Daystat.objects.create(
                user=self.user,
                date=self.date,
            )

    def test_week_calculation(self):
        """Корректность вычисления номера недели для объекта Daystat"""
        self.assertEqual(self.daystat.week, int(self.date.strftime('%W')))

    def test_calendar_view(self):
        """Доступ к 'daystats:calendar' и корректное использование шаблона"""
        response = self.client.get(reverse('daystats:calendar'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'daystats/calendar.html')

    def test_calendar_api_view(self):
        """Корректность работы API для календаря"""
        start_date = self.date - datetime.timedelta(days=30)
        end_date = self.date
        response = self.client.get(reverse('daystats:calendar_api'), {
            'start': start_date.isoformat(),
            'end': end_date.isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('Цикл', response.json()[0]['title'])

    def test_chart_view(self):
        """Доступ к 'daystats:chart' и корректное использование шаблона"""
        response = self.client.get(reverse('daystats:chart'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'daystats/chart.html')

    def test_chart_api_view(self):
        """Корректность работы API для графиков"""
        response = self.client.get(
            reverse('daystats:chart_api', args=['weight', 'month']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['title'], 'Вес, кг')

    def test_calories_summary_view(self):
        """Доступ к 'daystats:calories_summary'"""
        response = self.client.get(reverse('daystats:calories_summary'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'daystats/calories_summary.html')
        self.assertContains(response, 'Статистика по калориям')

    def test_unauthorized_access(self):
        """Недоступность страниц для неавторизованного пользователя"""
        self.client.logout()

        response = self.client.get(reverse('daystats:today'))
        self.assertRedirects(
            response, (f"{reverse('users:login')}"
                       + f"?next={reverse('daystats:today')}"))

        response = self.client.get(reverse('daystats:calendar'))
        self.assertRedirects(
            response, (f"{reverse('users:login')}"
                       + f"?next={reverse('daystats:calendar')}"))

        response = self.client.get(reverse('daystats:calendar_api'), {
            'start': self.date.isoformat(),
            'end': self.date.isoformat(),
        })
        self.assertEqual(response.status_code, 302)

        response = self.client.get(
            reverse('daystats:chart_api', args=['weight', 'month']))
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('daystats:calories_summary'))
        self.assertRedirects(
            response, (f"{reverse('users:login')}"
                       + f"?next={reverse('daystats:calories_summary')}"))


class DaystatFormTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser', password='password')
        self.date = datetime.date.today()

    def test_form_valid_data(self):
        """DaystatForm корректно валидируется с допустимыми данными"""
        form_data = {
            'calories': 1800,
            'weight': 68.5,
            'period_start': True,
        }
        form = DaystatForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_missing_required_data(self):
        """DaystatForm валидируется при отсутствии необязательных полей"""
        form_data = {
            'weight': 68.5,
        }
        form = DaystatForm(data=form_data)
        # Calories и period_start не обязательны
        self.assertTrue(form.is_valid())

    def test_form_invalid_calories(self):
        """DaystatForm отклоняет слишком высокое значение для калорий"""
        form_data = {
            'calories': 6000,  # Слишком много калорий
            'weight': 68.5,
            'period_start': True,
        }
        form = DaystatForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('calories', form.errors)

    def test_form_invalid_weight(self):
        """DaystatForm отклоняет слишком высокое значение для веса"""
        form_data = {
            'calories': 1800,
            'weight': 300,  # Слишком большой вес
            'period_start': False,
        }
        form = DaystatForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('weight', form.errors)

    def test_form_saving(self):
        """Корректность сохранения данных формы DaystatForm в базу данных"""
        form_data = {
            'calories': 1800,
            'weight': 68.5,
            'period_start': True,
        }
        form = DaystatForm(data=form_data)
        self.assertTrue(form.is_valid())

        daystat = form.save(commit=False)
        daystat.user = self.user
        daystat.date = self.date
        daystat.save()

        self.assertEqual(Daystat.objects.count(), 1)
        self.assertEqual(Daystat.objects.first().calories, 1800)
        self.assertEqual(Daystat.objects.first().weight, 68.5)
        self.assertTrue(Daystat.objects.first().period_start)
