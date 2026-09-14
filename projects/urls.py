from django.urls import path

from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('new/', views.project_create, name='project_create'),
    path('dashboard/', views.client_dashboard, name='client_dashboard'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('<int:pk>/edit/', views.project_update, name='project_update'),
    path('<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('<int:pk>/start/', views.project_start, name='project_start'),
    path('<int:pk>/complete/', views.project_complete, name='project_complete'),
    path('<int:pk>/cancel/', views.project_cancel, name='project_cancel'),
    path('<int:pk>/close/', views.project_cancel, name='project_close'),
    path('<int:pk>/workspace/', views.project_workspace, name='project_workspace'),
]
