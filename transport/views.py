"""transport/views.py — Transport management + live tracking endpoints"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import TransportRequest, TransportLeg, TransportCheckpoint, ColdChainLog
from .serializers import (
    TransportRequestSerializer, TransportLegSerializer,
    TransportCheckpointSerializer, ColdChainLogSerializer,
    TransportTrackingSerializer,
)
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def broadcast_transport_update(transport_id, data):
    """Push update to all WebSocket clients watching this transport."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'transport_{transport_id}',
            {'type': 'tracking_update', 'data': data}
        )
        # Also broadcast to all-transports admin feed
        async_to_sync(channel_layer.group_send)(
            'all_transports',
            {'type': 'transport_update', 'data': {'type': 'update', 'transport_id': transport_id, **data}}
        )
    except Exception:
        pass  # Channel layer not available in dev


class TransportRequestViewSet(viewsets.ModelViewSet):
    queryset = TransportRequest.objects.select_related(
        'origin_hospital', 'destination_hospital', 'organ_match'
    ).prefetch_related('legs__checkpoints', 'cold_chain_logs').order_by('-created_at')
    serializer_class = TransportRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        organ_type    = self.request.query_params.get('organ_type')
        if status_filter: qs = qs.filter(status=status_filter)
        if organ_type:    qs = qs.filter(organ_type=organ_type)
        return qs

    @action(detail=True, methods=['get'])
    def track(self, request, pk=None):
        """Live tracking state — used by WebSocket initial connect too."""
        transport = self.get_object()
        return Response(TransportTrackingSerializer(transport).data)

    @action(detail=True, methods=['post'])
    def status(self, request, pk=None):
        """Update transport status. Broadcasts via WebSocket."""
        transport = self.get_object()
        new_status = request.data.get('status')
        valid = ['pending','dispatched','in_transit','delayed','delivered','cancelled']
        if new_status not in valid:
            return Response({'error': f'Invalid status. Must be one of: {valid}'}, status=400)

        transport.status = new_status
        if new_status == 'delivered':
            transport.actual_arrival = timezone.now()
        transport.save()

        data = TransportTrackingSerializer(transport).data
        broadcast_transport_update(pk, {'type': 'status_update', **data})
        return Response(data)

    @action(detail=True, methods=['post'])
    def checkpoint(self, request, pk=None):
        """Field team posts GPS position. Broadcasts live to map."""
        transport = self.get_object()
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        note = request.data.get('note', '')

        if not lat or not lng:
            return Response({'error': 'latitude and longitude required'}, status=400)

        leg = transport.legs.filter(status='in_progress').first()
        if not leg:
            return Response({'error': 'No active leg found for this transport'}, status=400)

        cp = TransportCheckpoint.objects.create(
            leg=leg, latitude=lat, longitude=lng, note=note
        )
        broadcast_transport_update(pk, {
            'type': 'checkpoint',
            'transport_id': int(pk),
            'lat': float(lat), 'lng': float(lng),
            'note': note, 'timestamp': cp.timestamp.isoformat(),
        })
        return Response(TransportCheckpointSerializer(cp).data, status=201)

    @action(detail=True, methods=['post'], url_path='cold-chain')
    def cold_chain(self, request, pk=None):
        """IoT device posts temperature reading."""
        transport = self.get_object()
        temp = request.data.get('temperature_celsius')
        humidity = request.data.get('humidity_percent')

        if temp is None:
            return Response({'error': 'temperature_celsius required'}, status=400)

        log = ColdChainLog.objects.create(
            transport=transport,
            temperature_celsius=float(temp),
            humidity_percent=float(humidity) if humidity else None,
        )

        if log.is_breach:
            broadcast_transport_update(pk, {
                'type': 'temperature_breach',
                'transport_id': int(pk),
                'temperature': float(temp),
                'organ_type': transport.organ_type,
            })

        return Response(ColdChainLogSerializer(log).data, status=201)

    @action(detail=True, methods=['get'])
    def legs(self, request, pk=None):
        transport = self.get_object()
        return Response(TransportLegSerializer(transport.legs.all(), many=True).data)


class AllActiveTransportsView(viewsets.ViewSet):
    """Single endpoint that returns all active transports with full tracking state."""
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        transports = TransportRequest.objects.filter(
            status__in=['dispatched', 'in_transit', 'delayed']
        ).select_related('origin_hospital', 'destination_hospital').prefetch_related(
            'legs__checkpoints', 'cold_chain_logs'
        )
        return Response(TransportTrackingSerializer(transports, many=True).data)
