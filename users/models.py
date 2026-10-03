from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Gender(models.TextChoices):
        FEMALE = 'Ж', 'Женский'
        MALE = 'М', 'Мужской'

    gender = models.CharField(
        max_length=1,
        choices=Gender.choices,
        default=Gender.FEMALE,
        verbose_name='Пол',
    )

    class Meta(AbstractUser.Meta):
        # the users were created by the stock auth.User: its table is kept
        db_table = 'auth_user'

    @property
    def tracks_cycle(self):
        """Everything about the menstrual cycle is shown only to women."""
        return self.gender == self.Gender.FEMALE

    @property
    def palette(self):
        """The interface colours: pink for women, blue for men."""
        return 'blue' if self.gender == self.Gender.MALE else 'pink'
