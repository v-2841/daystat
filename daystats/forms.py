from django.core.exceptions import ValidationError
from django.forms import ModelForm, RadioSelect, TextInput
from django.forms.models import ModelChoiceIterator

from daystats.models import Daystat, Expense, ExpenseCategory, alphabetical


class DaystatForm(ModelForm):
    class Meta:
        model = Daystat
        fields = ['calories', 'weight', 'period_start']

    # short units: the fields are already labelled next to the input
    PLACEHOLDERS = {
        'calories': 'ккал',
        'weight': 'кг',
    }

    def __init__(self, *args, tracks_cycle=True, **kwargs):
        super().__init__(*args, **kwargs)
        for field, placeholder in self.PLACEHOLDERS.items():
            self.fields[field].widget.attrs['placeholder'] = placeholder
        # without the field a save keeps the stored cycle starts untouched
        if not tracks_cycle:
            del self.fields['period_start']


class AlphabeticalIterator(ModelChoiceIterator):
    def __iter__(self):
        if self.field.empty_label is not None:
            yield ('', self.field.empty_label)
        for category in sorted(self.queryset,
                               key=lambda item: alphabetical(item.name)):
            yield self.choice(category)


class ExpenseForm(ModelForm):
    class Meta:
        model = Expense
        fields = ['value', 'category', 'note']
        widgets = {
            # the radios are hidden, their labels are the chips
            'category': RadioSelect(attrs={'class': 'sr-only'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # the instance always comes with its user: only their categories
        category = self.fields['category']
        # set before the queryset, which hands the choices to the widget
        category.iterator = AlphabeticalIterator
        category.queryset = ExpenseCategory.objects.filter(
            user_id=self.instance.user_id,
        )
        category.empty_label = 'Без категории'


class ExpenseCategoryForm(ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name']
        widgets = {
            'name': TextInput(attrs={'placeholder': 'Например, продукты'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        taken = (
            ExpenseCategory.objects
            .filter(user_id=self.instance.user_id)
            .exclude(pk=self.instance.pk)
            .values_list('name', flat=True)
        )
        # compared in python: sqlite lower() leaves cyrillic as is
        if name.casefold() in {other.casefold() for other in taken}:
            raise ValidationError('Такая категория уже есть')
        return name
