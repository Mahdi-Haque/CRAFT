from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='notification_list'),
    path('<int:pk>/mark-as-read/', views.mark_notification_as_read, name='mark_as_read'),
    path('mark-all-as-read/', views.mark_all_notifications_as_read, name='mark_all_as_read'),
]
