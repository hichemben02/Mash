from django.urls import path
from . import views

urlpatterns = [
    path('', views.groups, name='groups'),
    path('checkview', views.checkview, name='checkview'),
    path('newgroup/', views.addgroup, name='addgroup'),
    path('<slug:slug>/', views.group, name='group'),
]