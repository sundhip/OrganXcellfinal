"""consent/models.py — Donor family consent workflow"""
from django.db import models

class ConsentRequest(models.Model):
    """Minimal stub — full model in the previous consent/ delivery."""
    donor = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='consent_requests')
    status = models.CharField(max_length=30, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Consent #{self.pk} — {self.donor}"
