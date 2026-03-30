"""ai_engine/tasks.py — Background AI tasks"""
from celery import shared_task
import logging
logger = logging.getLogger(__name__)

@shared_task
def ai_reorder_waiting_list():
    """Run AI reordering for all organ types every 30 minutes."""
    from organs.models import RecipientRequest
    organ_types = RecipientRequest.objects.filter(
        status='waiting'
    ).values_list('organ_type', flat=True).distinct()

    for organ_type in organ_types:
        try:
            _reorder_for_organ(organ_type)
            logger.info(f"AI reordered waiting list for: {organ_type}")
        except Exception as e:
            logger.error(f"AI reorder failed for {organ_type}: {e}")

    return f"AI reordering complete for {len(list(organ_types))} organ types"


def _reorder_for_organ(organ_type):
    """Internal: AI-score and tag waiting list entries."""
    import json
    import anthropic
    from django.conf import settings
    from django.utils import timezone
    from organs.models import RecipientRequest

    waiting = list(RecipientRequest.objects.filter(
        organ_type=organ_type, status='waiting'
    ).select_related('recipient__medical_profile')[:20])

    if len(waiting) < 2:
        return

    patients_data = []
    for req in waiting:
        r_profile = getattr(req.recipient, 'medical_profile', None)
        patients_data.append({
            'id': req.pk,
            'days_waiting': (timezone.now() - req.waiting_since).days,
            'priority': req.priority,
            'organ_data': req.organ_specific_data,
            'pra': getattr(r_profile, 'pra_score', None),
        })

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=600,
        messages=[{
            'role': 'user',
            'content': f"""Rank these {organ_type} transplant candidates by urgency. 
Return ONLY JSON: {{"ranking": [{{"id": N, "ai_urgency_score": 0-100}}]}}
Patients: {json.dumps(patients_data)}"""
        }]
    )

    try:
        result = json.loads(message.content[0].text)
        ranking = {r['id']: r['ai_urgency_score'] for r in result.get('ranking', [])}
        for req in waiting:
            score = ranking.get(req.pk)
            if score is not None:
                osd = req.organ_specific_data or {}
                osd['ai_urgency_score'] = score
                req.organ_specific_data = osd
                req.save(update_fields=['organ_specific_data'])
    except Exception as e:
        logger.error(f"Failed to parse AI ranking: {e}")
