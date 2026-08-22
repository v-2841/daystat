from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


User = get_user_model()


class Daystat(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='daystats',
        verbose_name='Пользователь',
    )
    date = models.DateField(
        verbose_name='Дата',
    )
    week = models.PositiveSmallIntegerField(
        editable=False,
        validators=[
            MaxValueValidator(53),
        ],
        verbose_name='Неделя',
    )
    calories = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MaxValueValidator(5000),
        ],
        verbose_name='Количество калорий, ккал',
    )
    weight = models.FloatField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(250),
        ],
        verbose_name='Вес, кг',
    )
    period_start = models.BooleanField(
        default=False,
        verbose_name='Начало цикла',
    )

    class Meta:
        ordering = ['-date', 'user']
        verbose_name = 'Статистика за день'
        verbose_name_plural = 'Статистики за день'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'date'],
                name='One user can only have one record per day',
            )
        ]

    def __str__(self):
        return f'{self.user} | {self.date.strftime("%d %B %Y г.")}'

    def save(self, *args, **kwargs):
        self.week = self.date.isocalendar().week
        super().save(*args, **kwargs)


class Expense(models.Model):
    value = models.PositiveIntegerField(
        verbose_name='Сумма',
    )
    note = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name='Примечание',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='expenses',
        verbose_name='Пользователь',
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Время создания',
    )

    class Meta:
        ordering = ['-created_at', 'user']
        verbose_name = 'Расход'
        verbose_name_plural = 'Расходы'

    def __str__(self):
        local_time = timezone.localtime(self.created_at)
        return f'{self.user} | {local_time.strftime("%d %B %Y г. %H:%M")}'

    @property
    def week(self):
        local_time = timezone.localtime(self.created_at)
        return local_time.isocalendar().week

    week.fget.short_description = 'Неделя'
