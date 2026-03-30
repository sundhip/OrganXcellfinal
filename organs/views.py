"""organs/views.py"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Organ, RecipientRequest, OrganMatch
from .serializers import OrganSerializer, RecipientRequestSerializer, OrganMatchSerializer
from .matching import calculate_compatibility


class OrganViewSet(viewsets.ModelViewSet):
    queryset = Organ.objects.select_related('donor', 'hospital').order_by('-created_at')
    serializer_class = OrganSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        organ_type    = self.request.query_params.get('organ_type')
        if status_filter: qs = qs.filter(status=status_filter)
        if organ_type:    qs = qs.filter(organ_type=organ_type)
        return qs

    @action(detail=True, methods=['get'])
    def find_matches(self, request, pk=None):
        """Run matching algorithm for this organ against all waiting recipients."""
        organ = self.get_object()
        waiting = RecipientRequest.objects.filter(
            organ_type=organ.organ_type, status='waiting'
        ).select_related('recipient__medical_profile', 'recipient', 'hospital')

        matches = []
        for req in waiting:
            score, breakdown = calculate_compatibility(organ, req)
            if score > 0:
                matches.append({
                    'recipient_request_id': req.pk,
                    'recipient': f"{req.recipient.first_name} {req.recipient.last_name}",
                    'blood_group': req.recipient.blood_group,
                    'priority': req.priority,
                    'score': round(score, 1),
                    'breakdown': breakdown,
                    'days_waiting': (timezone.now() - req.waiting_since).days,
                })

        matches.sort(key=lambda x: x['score'], reverse=True)
        return Response({'organ_id': pk, 'organ_type': organ.organ_type, 'matches': matches[:10]})


class RecipientRequestViewSet(viewsets.ModelViewSet):
    queryset = RecipientRequest.objects.select_related(
        'recipient__medical_profile', 'recipient', 'hospital'
    ).order_by('-created_at')
    serializer_class = RecipientRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        organ_type    = self.request.query_params.get('organ_type')
        priority      = self.request.query_params.get('priority')
        if status_filter: qs = qs.filter(status=status_filter)
        if organ_type:    qs = qs.filter(organ_type=organ_type)
        if priority:      qs = qs.filter(priority=priority)
        return qs


class OrganMatchViewSet(viewsets.ModelViewSet):
    queryset = OrganMatch.objects.select_related(
        'organ__donor', 'organ__hospital',
        'recipient_request__recipient', 'recipient_request__hospital',
    ).order_by('-matched_at')
    serializer_class = OrganMatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        match = self.get_object()
        match.status = 'approved'
        match.approved_at = timezone.now()
        match.save()
        match.organ.status = 'matched'
        match.organ.save()
        match.recipient_request.status = 'matched'
        match.recipient_request.save()
        return Response(OrganMatchSerializer(match).data)
