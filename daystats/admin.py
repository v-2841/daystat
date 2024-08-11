from django.contrib import admin

from daystats.models import Daystat


@admin.register(Daystat)
class DaystatAdmin(admin.ModelAdmin):
    list_display = ['date', 'user', 'calories', 'weight', 'period_start']

    # Не показывать время обновления при создании
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('updated_at',)
        return self.readonly_fields
