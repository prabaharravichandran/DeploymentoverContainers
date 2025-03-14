# myapp/urls.py
from django.urls import path
from .views import index, home

urlpatterns = [
    path('yield&fnm', index, name='index'),
    path('home', home, name='home'),
    path('', home, name='home'),
]
