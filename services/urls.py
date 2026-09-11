from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('', views.service_list, name='service_list'),
    path('new/', views.service_create, name='service_create'),
    path('<int:pk>/', views.service_detail, name='service_detail'),
    path('<int:pk>/edit/', views.service_update, name='service_update'),
    path('<int:pk>/delete/', views.service_delete, name='service_delete'),
    path('<int:pk>/toggle-active/', views.service_toggle_active, name='service_toggle_active'),
]
