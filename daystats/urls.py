from django.urls import path

from daystats import views


app_name = 'daystats'
urlpatterns = [
    path('', views.profile, name='profile'),
]
