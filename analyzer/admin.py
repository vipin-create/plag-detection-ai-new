# analyzer/admin.py
from django.contrib import admin
from .models import ScanReport, ReferenceDocument

from django.contrib import admin
from .models import ScanReport, ReferenceDocument

admin.site.register(ScanReport)
admin.site.register(ReferenceDocument)