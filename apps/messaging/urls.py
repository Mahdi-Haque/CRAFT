from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.conversation_list, name='conversation_list'),
    path('start/', views.start_conversation, name='start_conversation'),
    path('<int:pk>/', views.conversation_detail, name='conversation_detail'),
    path('<int:pk>/send/', views.send_message, name='send_message'),
]

