from django.urls import path

from daystats import views


app_name = 'daystats'
urlpatterns = [
    path('daystats/<str:date>/', views.today, name='daystats'),
    path('', views.today, name='today'),
]
