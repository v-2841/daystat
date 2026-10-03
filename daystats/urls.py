from django.urls import path
from django.views.generic import RedirectView

from daystats import views


app_name = 'daystats'
urlpatterns = [
    path('', views.home, name='home'),
    path('day/', views.day, name='day'),
    path('daystats/<str:date>/', views.day, name='daystats'),
    path('calendar/', views.calendar, name='calendar'),
    path('analytics/', views.analytics, name='analytics'),
    path('chart/<str:type>/<str:range>/',
         views.chart_api, name='chart_api'),
    path('cycle_weight_chart/api/',
         views.cycle_weight_chart_api, name='cycle_weight_chart_api'),
    path('expense_edit/<int:pk>/', views.expense_edit, name='expense_edit'),
    path('expenses/weeks/', views.expenses_weeks, name='expenses_weeks'),
    path('expenses/months/', views.expenses_months, name='expenses_months'),
    path('expenses/', views.expenses, name='expenses'),
    path('expenses/categories/', views.expense_categories,
         name='expense_categories'),
    path('expense_category_edit/<int:pk>/', views.expense_category_edit,
         name='expense_category_edit'),
    path('expense_category_delete/<int:pk>/', views.expense_category_delete,
         name='expense_category_delete'),
    path('expense_delete/<int:pk>/', views.expense_delete,
         name='expense_delete'),
    # legacy urls kept as redirects
    path('chart/', RedirectView.as_view(
        pattern_name='daystats:analytics', permanent=False)),
    path('cycle_weight_chart/', RedirectView.as_view(
        url='/analytics/?tab=cycle', permanent=False)),
    path('calories_summary/', RedirectView.as_view(
        url='/analytics/?tab=weeks', permanent=False)),
]
