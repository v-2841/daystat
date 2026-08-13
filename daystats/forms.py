from django.forms import ModelForm

from daystats.models import Daystat, Expense


class DaystatForm(ModelForm):
    class Meta:
        model = Daystat
        fields = ['calories', 'weight', 'period_start']

    # short units: the fields are already labelled next to the input
    PLACEHOLDERS = {
        'calories': 'ккал',
        'weight': 'кг',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field, placeholder in self.PLACEHOLDERS.items():
            self.fields[field].widget.attrs['placeholder'] = placeholder


class ExpenseForm(ModelForm):
    class Meta:
        model = Expense
        fields = ['value', 'note']
