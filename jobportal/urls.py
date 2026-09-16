from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('projects/', include('projects.urls')),
    path('applications/', include('applications.urls')),
    path('services/', include('services.urls')),
    path('messages/', include('apps.messaging.urls')),
    path('', views.home_view, name='home'),
]
