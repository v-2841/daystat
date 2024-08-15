from django.urls import path

from daystats import views


app_name = 'daystats'
urlpatterns = [
    path('daystats/<str:date>/', views.today, name='daystats'),
    path('calendar/', views.calendar, name='calendar'),
    path('calendar_api/', views.calendar_api, name='calendar_api'),
    path('chart/<str:type>/<str:range>/',
         views.chart_api, name='chart_api'),
    path('chart/', views.chart, name='chart'),
    path('calories_summary/', views.calories_summary, name='calories_summary'),
    path('', views.today, name='today'),
]
