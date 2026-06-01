from django.db import models
from django.conf import settings


class EmailDraft(models.Model):
    to = models.CharField(max_length=500)
    cc = models.CharField(max_length=500, blank=True)
    subject = models.CharField(max_length=500, blank=True)
    body = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_drafts',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Draft: {self.subject or '(no subject)'} → {self.to}"
