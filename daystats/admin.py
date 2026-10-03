from django.contrib import admin

from daystats.models import Daystat, Expense, ExpenseCategory


@admin.register(Daystat)
class DaystatAdmin(admin.ModelAdmin):
    list_display = ['date', 'user', 'calories',
                    'weight', 'period_start', 'week']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('week',)
        return self.readonly_fields


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'user']
    list_filter = ['user']
    search_fields = ['name']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'user', 'value', 'category', 'note',
                    'week']
    list_filter = ['user', 'category']
    # the category may be empty, and a bare select_related() skips such keys
    list_select_related = ['user', 'category']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('week',)
        return self.readonly_fields
