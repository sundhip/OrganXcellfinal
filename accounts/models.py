"""accounts/models.py"""
from django.contrib.auth.models import AbstractUser
from django.db import models


ROLE_CHOICES = [('admin','Admin'),('donor','Donor'),('recipient','Recipient'),('hospital','Hospital'),('doctor','Doctor')]
BLOOD_GROUPS = [('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-')]


class Hospital(models.Model):
    name                  = models.CharField(max_length=200)
    registration_number   = models.CharField(max_length=50, unique=True)
    address               = models.TextField()
    city                  = models.CharField(max_length=100)
    state                 = models.CharField(max_length=100)
    pincode               = models.CharField(max_length=10)
    phone                 = models.CharField(max_length=20)
    email                 = models.EmailField()
    latitude              = models.FloatField(null=True, blank=True)
    longitude             = models.FloatField(null=True, blank=True)
    is_verified           = models.BooleanField(default=False)
    has_transplant_facility= models.BooleanField(default=True)
    created_at            = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.city})"


class User(AbstractUser):
    email        = models.EmailField(unique=True)
    role         = models.CharField(max_length=20, choices=ROLE_CHOICES, default='recipient')
    blood_group  = models.CharField(max_length=5, choices=BLOOD_GROUPS, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    hospital     = models.ForeignKey(Hospital, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff')
    is_verified  = models.BooleanField(default=False)
    date_of_birth= models.DateField(null=True, blank=True)
    address      = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.get_full_name()} ({self.email}) — {self.role}"


class MedicalProfile(models.Model):
    user              = models.OneToOneField(User, on_delete=models.CASCADE, related_name='medical_profile')
    height            = models.FloatField(null=True, blank=True, help_text='cm')
    weight            = models.FloatField(null=True, blank=True, help_text='kg')
    hla_typing        = models.JSONField(default=dict, blank=True, help_text='{"A":[],"B":[],"DR":[]}')
    pra_score         = models.IntegerField(null=True, blank=True, help_text='0-100')
    medical_conditions= models.TextField(blank=True)
    allergies         = models.TextField(blank=True)
    current_medications=models.TextField(blank=True)
    updated_at        = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Medical Profile — {self.user}"
