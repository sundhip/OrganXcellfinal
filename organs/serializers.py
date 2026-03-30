"""organs/serializers.py"""
from rest_framework import serializers
from .models import Organ, RecipientRequest, OrganMatch


class OrganSerializer(serializers.ModelSerializer):
    donor_name = serializers.SerializerMethodField()
    donor_blood = serializers.CharField(source='donor.blood_group', read_only=True)
    hospital_name = serializers.CharField(source='hospital.name', read_only=True)

    class Meta:
        model = Organ
        fields = '__all__'

    def get_donor_name(self, obj):
        return f"{obj.donor.first_name} {obj.donor.last_name}"


class RecipientRequestSerializer(serializers.ModelSerializer):
    recipient = serializers.SerializerMethodField()
    hospital  = serializers.SerializerMethodField()
    days_waiting = serializers.SerializerMethodField()

    class Meta:
        model = RecipientRequest
        fields = '__all__'

    def get_recipient(self, obj):
        return {'id': obj.recipient_id, 'first_name': obj.recipient.first_name, 'last_name': obj.recipient.last_name, 'blood_group': obj.recipient.blood_group}

    def get_hospital(self, obj):
        return {'id': obj.hospital_id, 'name': obj.hospital.name} if obj.hospital else None

    def get_days_waiting(self, obj):
        from django.utils import timezone
        return (timezone.now() - obj.waiting_since).days


class OrganMatchSerializer(serializers.ModelSerializer):
    organ_type = serializers.CharField(source='organ.organ_type', read_only=True)
    recipient_name = serializers.SerializerMethodField()
    donor_blood = serializers.CharField(source='organ.donor.blood_group', read_only=True)
    recipient_blood = serializers.CharField(source='recipient_request.recipient.blood_group', read_only=True)

    class Meta:
        model = OrganMatch
        fields = '__all__'

    def get_recipient_name(self, obj):
        r = obj.recipient_request.recipient
        return f"{r.first_name} {r.last_name}"


# ── URLs ──────────────────────────────────────────────────
