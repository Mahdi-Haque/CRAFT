from django.urls import path

from . import views

app_name = 'applications'

urlpatterns = [
    path('project/<int:pk>/apply/', views.apply_to_project, name='project_apply'),
    path('project/<int:pk>/applicants/', views.applicants_list, name='applicants_list'),
    path('<int:pk>/withdraw/', views.withdraw_application, name='application_withdraw'),
    path('<int:pk>/accept/', views.accept_application, name='application_accept'),
    path('<int:pk>/reject/', views.reject_application, name='application_reject'),
    path('<int:pk>/status/<str:new_status>/', views.update_application_status, name='application_status'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
]
