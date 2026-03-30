"""organs/tasks.py"""
from celery import shared_task
import logging
logger = logging.getLogger(__name__)


@shared_task
def check_organ_expiry():
    """Every 15 min: mark expired organs and notify coordinators."""
    from .models import Organ
    from django.utils import timezone
    expired = Organ.objects.filter(status='available', expiry_time__lt=timezone.now())
    count = expired.count()
    expired.update(status='expired')
    if count:
        logger.warning(f"Marked {count} organs as expired")
    return f'Checked expiry: {count} expired'


@shared_task
def auto_match_new_organs():
    """Every 10 min: find matches for newly available organs."""
    from .models import Organ, RecipientRequest, OrganMatch
    from .matching import calculate_compatibility
    
    new_organs = Organ.objects.filter(status='available').select_related('donor__medical_profile')
    matched_count = 0
    
    for organ in new_organs:
        waiting = RecipientRequest.objects.filter(
            organ_type=organ.organ_type, status='waiting'
        ).select_related('recipient__medical_profile')[:10]
        
        best_score, best_req = 0, None
        for req in waiting:
            score, breakdown = calculate_compatibility(organ, req)
            if score > best_score:
                best_score, best_req = score, req
                best_breakdown = breakdown
        
        if best_req and best_score >= 40:
            match, created = OrganMatch.objects.get_or_create(
                organ=organ, recipient_request=best_req,
                defaults={'compatibility_score': best_score, 'match_breakdown': best_breakdown}
            )
            if created:
                matched_count += 1
                from notifications.tasks import send_match_notification
                send_match_notification.delay(match.pk)
    
    return f'Auto-matched {matched_count} organ(s)'
