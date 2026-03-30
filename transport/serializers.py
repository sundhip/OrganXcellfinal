"""transport/serializers.py"""
from rest_framework import serializers
from .models import TransportRequest, TransportLeg, TransportCheckpoint, ColdChainLog


class TransportCheckpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportCheckpoint
        fields = '__all__'


class ColdChainLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColdChainLog
        fields = '__all__'


class TransportLegSerializer(serializers.ModelSerializer):
    checkpoints = TransportCheckpointSerializer(many=True, read_only=True)
    latest_checkpoint = serializers.SerializerMethodField()

    class Meta:
        model = TransportLeg
        fields = '__all__'

    def get_latest_checkpoint(self, obj):
        cp = obj.checkpoints.last()
        return TransportCheckpointSerializer(cp).data if cp else None


class TransportRequestSerializer(serializers.ModelSerializer):
    legs = TransportLegSerializer(many=True, read_only=True)
    cold_chain_logs = ColdChainLogSerializer(many=True, read_only=True)
    time_remaining_minutes = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    progress_percent = serializers.FloatField(read_only=True)
    origin_hospital_name = serializers.CharField(source='origin_hospital.name', read_only=True)
    origin_city = serializers.CharField(source='origin_hospital.city', read_only=True)
    origin_lat = serializers.FloatField(source='origin_hospital.latitude', read_only=True)
    origin_lng = serializers.FloatField(source='origin_hospital.longitude', read_only=True)
    destination_hospital_name = serializers.CharField(source='destination_hospital.name', read_only=True)
    destination_city = serializers.CharField(source='destination_hospital.city', read_only=True)
    destination_lat = serializers.FloatField(source='destination_hospital.latitude', read_only=True)
    destination_lng = serializers.FloatField(source='destination_hospital.longitude', read_only=True)
    cold_chain_breaches = serializers.SerializerMethodField()
    latest_position = serializers.SerializerMethodField()

    class Meta:
        model = TransportRequest
        fields = '__all__'
        read_only_fields = ('ischaemic_limit_hrs', 'deadline', 'created_at', 'updated_at')

    def get_cold_chain_breaches(self, obj):
        return obj.cold_chain_logs.filter(is_breach=True).count()

    def get_latest_position(self, obj):
        """Return latest GPS coordinate from active leg checkpoints."""
        for leg in obj.legs.filter(status='in_progress'):
            cp = leg.checkpoints.last()
            if cp and cp.latitude:
                return {'lat': cp.latitude, 'lng': cp.longitude, 'timestamp': cp.timestamp}
        return None


class TransportTrackingSerializer(TransportRequestSerializer):
    """Lightweight serializer for WebSocket live updates."""
    class Meta(TransportRequestSerializer.Meta):
        fields = [
            'id', 'organ_type', 'status', 'priority',
            'time_remaining_minutes', 'is_overdue', 'progress_percent',
            'deadline', 'estimated_arrival', 'actual_arrival',
            'origin_hospital_name', 'origin_city', 'origin_lat', 'origin_lng',
            'destination_hospital_name', 'destination_city', 'destination_lat', 'destination_lng',
            'cold_chain_breaches', 'latest_position',
        ]
