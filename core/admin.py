from django.contrib import admin
from django.contrib.auth.models import Group


admin.site.site_title = 'DayStat'
admin.site.site_header = 'DayStat'
admin.site.index_title = 'Администрирование сайта'
admin.site.unregister(Group)
