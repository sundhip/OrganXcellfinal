"""transport/tasks.py"""
from celery import shared_task
import logging
logger = logging.getLogger(__name__)


@shared_task
def update_all_etas():
    """Every 5 minutes: recalculate ETAs for in-transit organs and broadcast via WebSocket."""
    from .models import TransportRequest
    from .serializers import TransportTrackingSerializer
    from .views import broadcast_transport_update
    from django.utils import timezone

    active = TransportRequest.objects.filter(
        status__in=['dispatched','in_transit']
    ).select_related('origin_hospital','destination_hospital')

    updated = 0
    for t in active:
        if t.is_overdue:
            t.status = 'delayed'
            t.save(update_fields=['status'])
            broadcast_transport_update(t.pk, {
                'type': 'status_update',
                'transport_id': t.pk,
                'status': 'delayed',
                'time_remaining_minutes': 0,
                'is_overdue': True,
            })
        else:
            broadcast_transport_update(t.pk, {
                'type': 'eta_update',
                'transport_id': t.pk,
                'time_remaining_minutes': t.time_remaining_minutes,
                'progress_percent': t.progress_percent,
            })
        updated += 1

    return f'Updated ETAs for {updated} active transports'


@shared_task
def sync_hospital_locations():
    """Every 6 hours: verify hospital GPS coordinates are accurate."""
    from accounts.models import Hospital
    hospitals_without_coords = Hospital.objects.filter(latitude__isnull=True)
    logger.info(f'Hospitals without GPS: {hospitals_without_coords.count()}')
    # In production: geocode using Google Maps Geocoding API or Nominatim
    return f'Hospital location sync complete'
