from django.db import models
from django.conf import settings

class ScanReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    text_content = models.TextField()
    plag_score = models.IntegerField(default=0)
    ai_score = models.IntegerField(default=0)
    scan_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, default='pending')
    scan_date = models.DateTimeField(auto_now_add=True)
    
    # The new field we are adding
    matched_sources = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.filename} - {self.scan_date.strftime('%Y-%m-%d')}"


class ReferenceDocument(models.Model):
    title = models.CharField(max_length=255, default="Untitled")
    # Made nullable so the terminal prompt disappears completely!
    file = models.FileField(upload_to='references/', null=True, blank=True)
    
    def __str__(self):
        return self.title