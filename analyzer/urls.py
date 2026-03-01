from django.urls import path
from . import views

urlpatterns = [
    # 1. This handles the empty homepage http://127.0.0.1:8000/
    path('', views.dashboard, name='index'), 
    
    # 2. Your specific tool pages
    path('plagiarism-scanner/', views.dashboard, name='dashboard'),
    path('ai-detector/', views.ai_detector, name='ai_detector'),
    path('humanizer/', views.humanizer, name='humanizer'),
    path('writing-assistant/', views.writing_assistant, name='writing_assistant'),
]