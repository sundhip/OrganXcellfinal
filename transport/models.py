"""transport/models.py"""
from django.db import models
from django.utils import timezone


ISCHAEMIC_LIMITS = {
    'heart': 4, 'lungs': 6, 'intestine': 8,
    'liver': 12, 'pancreas': 12, 'kidney': 24,
}

TRANSPORT_STATUS = [
    ('pending','Pending'),('dispatched','Dispatched'),('in_transit','In Transit'),
    ('delayed','Delayed'),('delivered','Delivered'),('cancelled','Cancelled'),
]

TRANSPORT_MODE = [
    ('ambulance','Ambulance'),('helicopter','Helicopter'),
    ('commercial_flight','Commercial Flight'),('charter_air','Charter Air'),
    ('train','Train'),
]


class TransportRequest(models.Model):
    organ_match         = models.ForeignKey('organs.OrganMatch', on_delete=models.SET_NULL, null=True, blank=True, related_name='transports')
    organ_type          = models.CharField(max_length=20)
    origin_hospital     = models.ForeignKey('accounts.Hospital', on_delete=models.PROTECT, related_name='transport_origins')
    destination_hospital= models.ForeignKey('accounts.Hospital', on_delete=models.PROTECT, related_name='transport_destinations')
    mode                = models.CharField(max_length=25, choices=TRANSPORT_MODE, default='ambulance')
    status              = models.CharField(max_length=20, choices=TRANSPORT_STATUS, default='pending')
    priority            = models.CharField(max_length=10, choices=[('critical','Critical'),('urgent','Urgent'),('standard','Standard')], default='urgent')
    ischaemic_limit_hrs = models.FloatField(editable=False)
    deadline            = models.DateTimeField(editable=False)
    estimated_arrival   = models.DateTimeField(null=True, blank=True)
    actual_arrival      = models.DateTimeField(null=True, blank=True)
    notes               = models.TextField(blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.pk:
            self.ischaemic_limit_hrs = ISCHAEMIC_LIMITS.get(self.organ_type, 12)
            self.deadline = timezone.now() + timezone.timedelta(hours=self.ischaemic_limit_hrs)
        super().save(*args, **kwargs)

    @property
    def time_remaining_minutes(self):
        delta = self.deadline - timezone.now()
        return max(0, int(delta.total_seconds() / 60))

    @property
    def is_overdue(self):
        return timezone.now() > self.deadline

    @property
    def progress_percent(self):
        if not self.estimated_arrival:
            return 0
        total = (self.estimated_arrival - self.created_at).total_seconds()
        elapsed = (timezone.now() - self.created_at).total_seconds()
        if total <= 0:
            return 0
        return min(100, round((elapsed / total) * 100, 1))

    def __str__(self):
        return f"Transport #{self.pk} — {self.organ_type} {self.origin_hospital} → {self.destination_hospital}"


class TransportLeg(models.Model):
    transport   = models.ForeignKey(TransportRequest, on_delete=models.CASCADE, related_name='legs')
    mode        = models.CharField(max_length=25, choices=TRANSPORT_MODE)
    driver_name = models.CharField(max_length=100, blank=True)
    vehicle_id  = models.CharField(max_length=50, blank=True)
    status      = models.CharField(max_length=20, choices=[('pending','Pending'),('in_progress','In Progress'),('completed','Completed')], default='pending')
    started_at  = models.DateTimeField(null=True, blank=True)
    completed_at= models.DateTimeField(null=True, blank=True)
    notes       = models.TextField(blank=True)

    def __str__(self):
        return f"Leg #{self.pk} ({self.mode}) for Transport #{self.transport_id}"


class TransportCheckpoint(models.Model):
    """GPS position pushed by field team."""
    leg       = models.ForeignKey(TransportLeg, on_delete=models.CASCADE, related_name='checkpoints')
    latitude  = models.FloatField()
    longitude = models.FloatField()
    note      = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']


class ColdChainLog(models.Model):
    """Temperature reading from IoT device in transport container."""
    transport           = models.ForeignKey(TransportRequest, on_delete=models.CASCADE, related_name='cold_chain_logs')
    temperature_celsius = models.FloatField()
    humidity_percent    = models.FloatField(null=True, blank=True)
    is_breach           = models.BooleanField(default=False)
    timestamp           = models.DateTimeField(auto_now_add=True)

    SAFE_RANGES = {'pancreas': (0, 2), 'default': (0, 4)}

    def save(self, *args, **kwargs):
        low, high = self.SAFE_RANGES.get(self.transport.organ_type, self.SAFE_RANGES['default'])
        self.is_breach = not (low <= self.temperature_celsius <= high)
        super().save(*args, **kwargs)
        if self.is_breach:
            from notifications.tasks import send_cold_chain_breach_alert
            send_cold_chain_breach_alert.delay(self.transport_id, self.temperature_celsius)

    class Meta:
        ordering = ['-timestamp']
