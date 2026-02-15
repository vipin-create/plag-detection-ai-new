from django.db import models
from django.conf import settings  # <--- This is the key fix

class ScanReport(models.Model):
    # We use settings.AUTH_USER_MODEL instead of the default User
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    filename = models.CharField(max_length=255, default="Text Scan")
    text_content = models.TextField()
    plag_score = models.IntegerField()
    ai_score = models.IntegerField()
    scan_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.filename} - {self.scan_date}"