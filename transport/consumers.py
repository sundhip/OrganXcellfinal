"""
transport/consumers.py — WebSocket consumer for live organ tracking
Each transport gets its own room: ws://host/ws/transport/{id}/
Frontend connects and receives real-time position + status updates.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class TransportTrackingConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.transport_id = self.scope['url_route']['kwargs']['transport_id']
        self.room_group = f'transport_{self.transport_id}'

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

        # Send current state immediately on connect
        state = await self.get_transport_state()
        await self.send(text_data=json.dumps({'type': 'initial_state', 'data': state}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        """Field team pushes GPS checkpoint via WebSocket."""
        data = json.loads(text_data)
        msg_type = data.get('type')

        if msg_type == 'checkpoint':
            await self.save_checkpoint(data)
            # Broadcast to all connected clients for this transport
            await self.channel_layer.group_send(self.room_group, {
                'type': 'tracking_update',
                'data': {
                    'type': 'checkpoint',
                    'transport_id': self.transport_id,
                    'lat': data.get('lat'),
                    'lng': data.get('lng'),
                    'note': data.get('note', ''),
                    'timestamp': data.get('timestamp'),
                }
            })
        elif msg_type == 'status_update':
            await self.update_transport_status(data.get('status'))
            state = await self.get_transport_state()
            await self.channel_layer.group_send(self.room_group, {
                'type': 'tracking_update',
                'data': {'type': 'status_update', **state}
            })
        elif msg_type == 'temperature':
            await self.save_temperature(data.get('temperature'), data.get('humidity'))
            await self.channel_layer.group_send(self.room_group, {
                'type': 'tracking_update',
                'data': {
                    'type': 'temperature',
                    'transport_id': self.transport_id,
                    'temperature': data.get('temperature'),
                    'is_breach': data.get('temperature', 0) > 4,
                }
            })

    async def tracking_update(self, event):
        """Called when group_send fires — relays to this WebSocket client."""
        await self.send(text_data=json.dumps(event['data']))

    @database_sync_to_async
    def get_transport_state(self):
        from transport.models import TransportRequest
        from transport.serializers import TransportTrackingSerializer
        try:
            tr = TransportRequest.objects.select_related(
                'origin_hospital', 'destination_hospital', 'organ_match'
            ).prefetch_related('legs__checkpoints').get(pk=self.transport_id)
            return TransportTrackingSerializer(tr).data
        except TransportRequest.DoesNotExist:
            return {'error': 'Transport not found'}

    @database_sync_to_async
    def save_checkpoint(self, data):
        from transport.models import TransportLeg, TransportCheckpoint
        leg = TransportLeg.objects.filter(
            transport_id=self.transport_id, status='in_progress'
        ).first()
        if leg:
            TransportCheckpoint.objects.create(
                leg=leg,
                latitude=data.get('lat'),
                longitude=data.get('lng'),
                note=data.get('note', ''),
            )

    @database_sync_to_async
    def update_transport_status(self, new_status):
        from transport.models import TransportRequest
        from django.utils import timezone
        TransportRequest.objects.filter(pk=self.transport_id).update(
            status=new_status,
            actual_arrival=timezone.now() if new_status == 'delivered' else None,
        )

    @database_sync_to_async
    def save_temperature(self, temp, humidity):
        from transport.models import ColdChainLog, TransportRequest
        try:
            tr = TransportRequest.objects.get(pk=self.transport_id)
            ColdChainLog.objects.create(
                transport=tr,
                temperature_celsius=temp,
                humidity_percent=humidity,
            )
        except Exception:
            pass


# ── ALL TRANSPORTS FEED (admin dashboard) ─────────────────────────────────
class AllTransportsFeedConsumer(AsyncWebsocketConsumer):
    """Admin connects to this to get updates from ALL active transports."""

    async def connect(self):
        self.group = 'all_transports'
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        # Send all active transports on connect
        data = await self.get_all_active()
        await self.send(text_data=json.dumps({'type': 'all_transports', 'data': data}))

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group, self.channel_name)

    async def transport_update(self, event):
        await self.send(text_data=json.dumps(event['data']))

    @database_sync_to_async
    def get_all_active(self):
        from transport.models import TransportRequest
        from transport.serializers import TransportTrackingSerializer
        transports = TransportRequest.objects.filter(
            status__in=['dispatched', 'in_transit', 'delayed']
        ).select_related('origin_hospital', 'destination_hospital').prefetch_related(
            'legs__checkpoints', 'cold_chain_logs'
        )
        return TransportTrackingSerializer(transports, many=True).data
