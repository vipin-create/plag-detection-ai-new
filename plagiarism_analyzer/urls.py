from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # This connects to the new file we made in the analyzer folder
    path('', include('analyzer.urls')), 
    
    # This keeps your login/signup working (since you have an accounts app)
    path('accounts/', include('accounts.urls')), 
]