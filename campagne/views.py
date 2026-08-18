from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status as http_status, viewsets, permissions
from .models import CritereSelection, Campagne, Referentiel, ReunionInformation
from .serializers import (
    CampagneSerializer,
    CritereSelectionSerializer,
    ReferentielSerializer,
    ReunionInformationSerializer
)
from accounts.permissions import HasRole, IsAccountActive
from accounts.models import User


class ReferentielViewSet(viewsets.ModelViewSet):
    queryset = Referentiel.objects.all()
    serializer_class = ReferentielSerializer
    permission_classes = [permissions.IsAuthenticated, HasRole.with_roles(User.Role.ADMIN)]


class CritereSelectionViewSet(viewsets.ModelViewSet):
    queryset = CritereSelection.objects.all()
    serializer_class = CritereSelectionSerializer
    permission_classes = [permissions.IsAuthenticated, HasRole.with_roles(User.Role.ADMIN)]


class CampagneViewSet(viewsets.ModelViewSet):
    queryset = Campagne.objects.all()
    serializer_class = CampagneSerializer
    permission_classes = [permissions.IsAuthenticated, HasRole.with_roles(User.Role.ADMIN)]

    @action(detail=True, methods=['post'])
    def publier(self, request, pk=None):
        campagne = self.get_object()
        if campagne.status != Campagne.Status.BROUILLON:
            return Response(
                {"error": "Seule une campagne en brouillon peut être publiée."},
                status=http_status.HTTP_409_CONFLICT,
            )
        campagne.status = Campagne.Status.PUBLIEE
        campagne.save()
        return Response(self.get_serializer(campagne).data)

    @action(detail=True, methods=['post'])
    def cloturer(self, request, pk=None):
        campagne = self.get_object()
        if campagne.status != Campagne.Status.PUBLIEE:
            return Response(
                {"error": "Seule une campagne publiée peut être clôturée."},
                status=http_status.HTTP_409_CONFLICT,
            )
        campagne.status = Campagne.Status.CLOTUREE
        campagne.save()
        return Response(self.get_serializer(campagne).data)


class ReunionInformationViewSet(viewsets.ModelViewSet):
    queryset = ReunionInformation.objects.all()
    serializer_class = ReunionInformationSerializer
    permission_classes = [permissions.IsAuthenticated, HasRole.with_roles(User.Role.ADMIN)]
