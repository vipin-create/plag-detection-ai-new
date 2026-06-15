from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('ai-detector/', views.ai_detector, name='ai_detector'),
    path('humanizer/', views.humanizer, name='humanizer'),
    path('writing-assistant/', views.writing_assistant, name='writing_assistant'),
    
    # Notice: The old 'webhook/copyleaks/' path has been completely removed!
]