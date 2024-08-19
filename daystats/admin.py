from django.contrib import admin

from daystats.models import Daystat, Expense


@admin.register(Daystat)
class DaystatAdmin(admin.ModelAdmin):
    list_display = ['date', 'user', 'calories',
                    'weight', 'period_start', 'week']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('week',)
        return self.readonly_fields


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'user', 'value', 'note', 'week']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('week',)
        return self.readonly_fields
