"""
ai_engine/views.py — All 6 AI features powered by Claude API
=============================================================
1. Match Score Explainer  — why did this match score X?
2. Organ Survival Predictor — probability of successful transplant
3. Smart Waiting List Reorder — AI re-ranks queue
4. AI Chatbot — donor/recipient assistant
5. Map Route Optimizer — best transport route
6. Allocation Advisor — full case recommendation
"""
import json
import anthropic
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from organs.models import Organ, RecipientRequest, OrganMatch
from organs.matching import calculate_compatibility
from transport.models import TransportRequest

User = get_user_model()


def get_claude():
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


# ── 1. MATCH SCORE EXPLAINER ──────────────────────────────────────────────
class MatchExplainerView(APIView):
    """
    POST /api/ai/explain-match/
    Body: { "match_id": 42 }
    Returns a detailed human-readable explanation of why a match scored as it did.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        match_id = request.data.get('match_id')
        try:
            match = OrganMatch.objects.select_related(
                'organ__donor__medical_profile',
                'organ__hospital',
                'recipient_request__recipient__medical_profile',
                'recipient_request__hospital',
            ).get(pk=match_id)
        except OrganMatch.DoesNotExist:
            return Response({'error': 'Match not found'}, status=404)

        organ = match.organ
        req   = match.recipient_request
        breakdown = match.match_breakdown or {}

        prompt = f"""You are OrganXcell's AI medical advisor. Explain this organ match result in clear, 
compassionate language for a transplant coordinator.

MATCH DETAILS:
- Organ: {organ.organ_type.title()}
- Compatibility Score: {match.compatibility_score:.1f}/100
- Donor Blood Group: {organ.donor.blood_group}
- Recipient Blood Group: {req.recipient.blood_group}
- Donation Type: {organ.donation_type}

SCORE BREAKDOWN:
{json.dumps(breakdown, indent=2)}

Write a 3-paragraph explanation:
1. Overall assessment (is this a good match? why?)
2. Key strengths of this match
3. Any concerns or factors the team should watch

Be specific, cite the actual numbers, and end with a clear recommendation (Proceed / Review / Caution)."""

        client = get_claude()
        message = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=600,
            messages=[{'role': 'user', 'content': prompt}]
        )
        explanation = message.content[0].text

        return Response({
            'match_id': match_id,
            'score': match.compatibility_score,
            'explanation': explanation,
            'breakdown': breakdown,
        })


# ── 2. ORGAN SURVIVAL PREDICTOR ───────────────────────────────────────────
class SurvivalPredictorView(APIView):
    """
    POST /api/ai/predict-survival/
    Body: { "match_id": 42 }
    Returns 1-year, 5-year survival probability + key risk factors.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        match_id = request.data.get('match_id')
        try:
            match = OrganMatch.objects.select_related(
                'organ__donor',
                'recipient_request__recipient__medical_profile',
            ).get(pk=match_id)
        except OrganMatch.DoesNotExist:
            return Response({'error': 'Match not found'}, status=404)

        r_profile = getattr(match.recipient_request.recipient, 'medical_profile', None)
        osd = match.recipient_request.organ_specific_data or {}

        prompt = f"""You are a transplant outcomes prediction AI. Based on the following case data,
predict survival probabilities and key risk factors. Return ONLY valid JSON, no other text.

CASE DATA:
- Organ: {match.organ.organ_type}
- Compatibility Score: {match.compatibility_score:.1f}/100
- Match Breakdown: {json.dumps(match.match_breakdown or {}, indent=2)}
- Recipient PRA Score: {getattr(r_profile, 'pra_score', 'Unknown')}
- Recipient Medical Conditions: {getattr(r_profile, 'medical_conditions', 'Not specified')}
- Organ-Specific Data: {json.dumps(osd, indent=2)}

Return JSON exactly like this:
{{
  "one_year_survival": 87,
  "five_year_survival": 72,
  "confidence": "high",
  "risk_factors": ["factor 1", "factor 2", "factor 3"],
  "protective_factors": ["factor 1", "factor 2"],
  "recommendation": "one sentence recommendation",
  "comparable_outcomes": "brief comparison to national averages"
}}"""

        client = get_claude()
        message = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=400,
            messages=[{'role': 'user', 'content': prompt}]
        )
        try:
            result = json.loads(message.content[0].text)
        except json.JSONDecodeError:
            result = {'error': 'Could not parse AI response', 'raw': message.content[0].text}

        return Response(result)


# ── 3. SMART WAITING LIST REORDER ─────────────────────────────────────────
class WaitingListReorderView(APIView):
    """
    POST /api/ai/reorder-waitlist/
    Body: { "organ_type": "kidney" }
    AI re-ranks the waiting list considering all factors holistically.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        organ_type = request.data.get('organ_type', 'kidney')
        waiting = RecipientRequest.objects.filter(
            organ_type=organ_type, status='waiting'
        ).select_related('recipient__medical_profile', 'recipient')[:20]

        if not waiting:
            return Response({'error': 'No patients on waiting list for this organ type'}, status=404)

        patients_data = []
        for i, req in enumerate(waiting):
            r_profile = getattr(req.recipient, 'medical_profile', None)
            patients_data.append({
                'id': req.pk,
                'patient': f"{req.recipient.first_name} {req.recipient.last_name}",
                'days_waiting': ((__import__('django.utils.timezone', fromlist=['timezone']).timezone.now() - req.waiting_since).days),
                'priority': req.priority,
                'organ_data': req.organ_specific_data,
                'pra': getattr(r_profile, 'pra_score', None),
                'conditions': getattr(r_profile, 'medical_conditions', ''),
            })

        prompt = f"""You are OrganXcell's AI allocation advisor. Re-rank this {organ_type} waiting list 
by medical urgency, considering ALL factors holistically — not just one metric.

CURRENT WAITING LIST:
{json.dumps(patients_data, indent=2)}

Return ONLY valid JSON — a reordered list with reasoning:
{{
  "reordered_list": [
    {{"id": 1, "new_rank": 1, "reason": "brief reason", "urgency_score": 95}},
    ...
  ],
  "ai_notes": "Overall observations about this waiting list",
  "algorithm_used": "brief description of ranking logic"
}}"""

        client = get_claude()
        message = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=800,
            messages=[{'role': 'user', 'content': prompt}]
        )
        try:
            result = json.loads(message.content[0].text)
        except json.JSONDecodeError:
            result = {'raw': message.content[0].text}

        return Response({'organ_type': organ_type, 'result': result})


# ── 4. AI CHATBOT ─────────────────────────────────────────────────────────
class ChatbotView(APIView):
    """
    POST /api/ai/chat/
    Body: { "message": "...", "role": "donor|recipient|admin", "history": [...] }
    Conversational AI assistant for all user types.
    """
    permission_classes = [permissions.IsAuthenticated]

    SYSTEM_PROMPTS = {
        'donor': """You are OrganXcell's compassionate donor support assistant. 
Help organ donors and their families understand the donation process, answer questions about 
consent, medical evaluation, what happens after donation, and emotional support. 
Be warm, clear, and reassuring. Never give specific medical advice — refer to their coordinator.""",

        'recipient': """You are OrganXcell's recipient support assistant. 
Help transplant recipients understand the waiting list, matching process, what to expect before 
and after surgery, medications, and follow-up care. Be empathetic and clear.
Never give specific medical advice — refer to their transplant team.""",

        'admin': """You are OrganXcell's clinical decision support assistant.
Help transplant coordinators and admins understand match scores, allocation decisions, 
protocol questions, and system usage. Provide data-driven, concise answers.""",

        'hospital': """You are OrganXcell's hospital operations assistant.
Help hospital staff with organ reporting, consent procedures, transport coordination,
and system workflows. Be precise and action-oriented.""",
    }

    def post(self, request):
        message = request.data.get('message', '').strip()
        role    = request.data.get('role', 'recipient')
        history = request.data.get('history', [])

        if not message:
            return Response({'error': 'Message is required'}, status=400)

        system_prompt = self.SYSTEM_PROMPTS.get(role, self.SYSTEM_PROMPTS['recipient'])

        # Build message history (max last 10 turns)
        messages = []
        for h in history[-10:]:
            if h.get('role') in ('user', 'assistant') and h.get('content'):
                messages.append({'role': h['role'], 'content': h['content']})
        messages.append({'role': 'user', 'content': message})

        client = get_claude()
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=500,
            system=system_prompt,
            messages=messages,
        )
        reply = response.content[0].text

        return Response({
            'reply': reply,
            'role': role,
        })


# ── 5. MAP ROUTE OPTIMIZER ────────────────────────────────────────────────
class RouteOptimizerView(APIView):
    """
    POST /api/ai/optimize-route/
    Body: { "transport_id": 42 } OR { "organ_type": "heart", "origin": "Chennai", "destination": "Hyderabad" }
    AI recommends optimal transport method and route.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        transport_id = request.data.get('transport_id')
        organ_type   = request.data.get('organ_type', 'heart')
        origin       = request.data.get('origin', 'Unknown')
        destination  = request.data.get('destination', 'Unknown')
        time_remaining = request.data.get('time_remaining_minutes', 240)

        if transport_id:
            try:
                tr = TransportRequest.objects.select_related(
                    'origin_hospital', 'destination_hospital'
                ).get(pk=transport_id)
                organ_type     = tr.organ_type
                origin         = f"{tr.origin_hospital.city}, {tr.origin_hospital.state}"
                destination    = f"{tr.destination_hospital.city}, {tr.destination_hospital.state}"
                time_remaining = tr.time_remaining_minutes
            except TransportRequest.DoesNotExist:
                return Response({'error': 'Transport not found'}, status=404)

        ischaemic_limits = {
            'heart': 240, 'lungs': 360, 'liver': 720,
            'pancreas': 720, 'kidney': 1440, 'intestine': 480
        }
        limit = ischaemic_limits.get(organ_type, 720)

        prompt = f"""You are OrganXcell's AI transport optimizer for organ logistics in India.

TRANSPORT CASE:
- Organ: {organ_type.title()}
- Origin: {origin}
- Destination: {destination}  
- Time remaining in ischaemic window: {time_remaining} minutes
- Total ischaemic limit: {limit} minutes
- Time elapsed: {limit - time_remaining} minutes

Analyze and return ONLY valid JSON:
{{
  "recommended_mode": "helicopter|ambulance|commercial_flight|charter_air|train",
  "estimated_travel_time_minutes": 90,
  "urgency_level": "critical|urgent|standard",
  "route_steps": [
    {{"step": 1, "action": "description", "duration_minutes": 10}},
    {{"step": 2, "action": "description", "duration_minutes": 45}}
  ],
  "alternative_routes": [
    {{"mode": "alternative mode", "time_minutes": 120, "risk": "higher risk reason"}}
  ],
  "risk_assessment": "brief risk paragraph",
  "recommendation": "clear one-line recommendation",
  "backup_hospitals": ["hospital1", "hospital2"]
}}"""

        client = get_claude()
        message = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=600,
            messages=[{'role': 'user', 'content': prompt}]
        )
        try:
            result = json.loads(message.content[0].text)
        except json.JSONDecodeError:
            result = {'raw': message.content[0].text}

        return Response({
            'transport_id': transport_id,
            'organ_type': organ_type,
            'route': result,
        })


# ── 6. ALLOCATION ADVISOR ─────────────────────────────────────────────────
class AllocationAdvisorView(APIView):
    """
    POST /api/ai/allocate/
    Body: { "organ_id": 42 }
    AI reviews ALL potential recipients and gives a full allocation recommendation.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        organ_id = request.data.get('organ_id')
        try:
            organ = Organ.objects.select_related(
                'donor__medical_profile', 'hospital'
            ).get(pk=organ_id, status='available')
        except Organ.DoesNotExist:
            return Response({'error': 'Organ not found or not available'}, status=404)

        # Get all potential recipients and run matching
        waiting = RecipientRequest.objects.filter(
            organ_type=organ.organ_type, status='waiting'
        ).select_related('recipient__medical_profile', 'recipient__hospital', 'recipient')[:15]

        match_results = []
        for req in waiting:
            score, breakdown = calculate_compatibility(organ, req)
            if score > 0:
                match_results.append({
                    'recipient_id': req.pk,
                    'patient': f"{req.recipient.first_name} {req.recipient.last_name}",
                    'score': round(score, 1),
                    'priority': req.priority,
                    'breakdown': breakdown,
                    'organ_data': req.organ_specific_data,
                    'days_waiting': ((__import__('django.utils.timezone', fromlist=['timezone']).timezone.now() - req.waiting_since).days),
                })

        match_results.sort(key=lambda x: x['score'], reverse=True)

        prompt = f"""You are OrganXcell's Chief Allocation AI Advisor. A {organ.organ_type} organ 
is available and needs to be allocated. Analyse ALL candidates and give a definitive recommendation.

AVAILABLE ORGAN:
- Type: {organ.organ_type.title()}
- Donor Blood Group: {organ.donor.blood_group}
- Hospital: {organ.hospital.name if organ.hospital else 'Unknown'}
- Donation Type: {organ.donation_type}

TOP CANDIDATES (scored by algorithm):
{json.dumps(match_results[:8], indent=2)}

Provide a comprehensive allocation recommendation. Return ONLY valid JSON:
{{
  "primary_recommendation": {{
    "recipient_id": 1,
    "patient_name": "Name",
    "score": 87.3,
    "rationale": "detailed 2-sentence rationale"
  }},
  "backup_recommendation": {{
    "recipient_id": 2,
    "patient_name": "Name",
    "rationale": "brief rationale"
  }},
  "concerns": ["concern 1", "concern 2"],
  "additional_tests_recommended": ["test 1", "test 2"],
  "time_sensitivity": "critical|urgent|standard",
  "overall_assessment": "2-sentence overall assessment",
  "confidence_level": "high|medium|low"
}}"""

        client = get_claude()
        message = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=700,
            messages=[{'role': 'user', 'content': prompt}]
        )
        try:
            result = json.loads(message.content[0].text)
        except json.JSONDecodeError:
            result = {'raw': message.content[0].text}

        return Response({
            'organ_id': organ_id,
            'organ_type': organ.organ_type,
            'candidates_evaluated': len(match_results),
            'recommendation': result,
            'all_scores': match_results,
        })
