from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


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
    calories = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MaxValueValidator(10000),
        ],
        verbose_name='Количество калорий, ккал',
    )
    weight = models.FloatField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(500),
        ],
        verbose_name='Вес, кг',
    )
    period_start = models.BooleanField(
        default=False,
        verbose_name='Начало месячных',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Время обновления',
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
        return f'{self.user} | {self.date}'
