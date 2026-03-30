"""organs/models.py"""
from django.db import models
from django.utils import timezone


ORGAN_TYPES = [('heart','Heart'),('liver','Liver'),('kidney','Kidney'),('lungs','Lungs'),('pancreas','Pancreas'),('intestine','Intestine')]
PRIORITY    = [('critical','Critical'),('urgent','Urgent'),('high','High'),('moderate','Moderate'),('low','Low')]
DONATION    = [('deceased','Deceased'),('living','Living'),('dcd','DCD')]


class Organ(models.Model):
    donor             = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='donated_organs')
    organ_type        = models.CharField(max_length=20, choices=ORGAN_TYPES)
    status            = models.CharField(max_length=20, choices=[('available','Available'),('matched','Matched'),('harvested','Harvested'),('transplanted','Transplanted'),('expired','Expired')], default='available')
    donation_type     = models.CharField(max_length=20, choices=DONATION, default='deceased')
    hospital          = models.ForeignKey('accounts.Hospital', on_delete=models.SET_NULL, null=True, blank=True)
    harvested_at      = models.DateTimeField(default=timezone.now)
    expiry_time       = models.DateTimeField(null=True, blank=True)
    organ_specific_data= models.JSONField(default=dict, blank=True)
    notes             = models.TextField(blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.organ_type.title()} from {self.donor}"


class RecipientRequest(models.Model):
    recipient         = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='requests')
    organ_type        = models.CharField(max_length=20, choices=ORGAN_TYPES)
    status            = models.CharField(max_length=20, choices=[('waiting','Waiting'),('matched','Matched'),('transplanted','Transplanted'),('inactive','Inactive')], default='waiting')
    priority          = models.CharField(max_length=20, choices=PRIORITY, default='urgent')
    organ_specific_data= models.JSONField(default=dict, blank=True)
    hospital          = models.ForeignKey('accounts.Hospital', on_delete=models.SET_NULL, null=True, blank=True)
    waiting_since     = models.DateTimeField(default=timezone.now)
    doctor_notes      = models.TextField(blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.organ_type} request — {self.recipient}"


class OrganMatch(models.Model):
    organ             = models.ForeignKey(Organ, on_delete=models.CASCADE, related_name='matches')
    recipient_request = models.ForeignKey(RecipientRequest, on_delete=models.CASCADE, related_name='matches')
    compatibility_score= models.FloatField()
    match_breakdown   = models.JSONField(default=dict, blank=True)
    status            = models.CharField(max_length=20, choices=[('pending','Pending'),('approved','Approved'),('rejected','Rejected'),('completed','Completed')], default='pending')
    matched_at        = models.DateTimeField(auto_now_add=True)
    approved_at       = models.DateTimeField(null=True, blank=True)
    notes             = models.TextField(blank=True)

    class Meta:
        unique_together = ['organ','recipient_request']

    def __str__(self):
        return f"Match #{self.pk}: {self.organ} → {self.recipient_request} ({self.compatibility_score:.1f}%)"
