from django.contrib import admin
from .models import CustomUser  # Make sure this matches your actual class name!

# Register your models here.
admin.site.register(CustomUser)