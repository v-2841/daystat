from django.forms import ModelForm

from daystats.models import Daystat, Expense


class DaystatForm(ModelForm):
    class Meta:
        model = Daystat
        fields = ['calories', 'weight', 'period_start']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs[
                'placeholder'] = self.fields[field].label


class ExpenseForm(ModelForm):
    class Meta:
        model = Expense
        fields = ['value', 'note']
