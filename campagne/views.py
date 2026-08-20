from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status as http_status, viewsets, permissions
from formulaire.permissions import IsAdministrateur
from .models import CritereSelection, Campagne, Referentiel, ReunionInformation, CreneauRI
from .serializers import (
    CampagneSerializer,
    CritereSelectionSerializer,
    ReferentielSerializer,
    ReunionInformationSerializer,
    CreneauRISerializer,
)
from accounts.permissions import HasRole, IsAccountActive
from accounts.models import User


class ReferentielViewSet(viewsets.ModelViewSet):
    queryset = Referentiel.objects.all()
    serializer_class = ReferentielSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdministrateur()]
        return [permissions.IsAuthenticated()]


class CritereSelectionViewSet(viewsets.ModelViewSet):
    queryset = CritereSelection.objects.all()
    serializer_class = CritereSelectionSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdministrateur()]
        return [permissions.IsAuthenticated()]


class CampagneViewSet(viewsets.ModelViewSet):
    queryset = Campagne.objects.all()
    serializer_class = CampagneSerializer


    def get_permissions(self):
        if self.action == 'reunion_information':
            if self.request.method in ['POST', 'PATCH', 'DELETE']:
                return [permissions.IsAuthenticated(), IsAdministrateur()]
            return [permissions.IsAuthenticated()]
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'publier', 'cloturer']:
            return [permissions.IsAuthenticated(), IsAdministrateur()]
        return [permissions.IsAuthenticated()]

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

    @action(detail=True, methods=['get', 'post', 'patch', 'delete'], url_path='reunion-information')
    def reunion_information(self, request, pk=None):
        campagne = self.get_object()
        ri = getattr(campagne, 'reunion_information', None)

        if request.method == 'GET':
            if not ri:
                return Response(
                    {"detail": "Aucune réunion d'information planifiée pour cette campagne."},
                    status=http_status.HTTP_404_NOT_FOUND,
                )
            serializer = ReunionInformationSerializer(ri)
            return Response(serializer.data)

        if request.method == 'POST':
            if ri:
                return Response(
                    {"detail": "Cette campagne possède déjà une réunion d'information."},
                    status=http_status.HTTP_400_BAD_REQUEST,
                )
            serializer = ReunionInformationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(campagne=campagne)
            return Response(serializer.data, status=http_status.HTTP_201_CREATED)

        if request.method == 'PATCH':
            if not ri:
                return Response(
                    {"detail": "Aucune réunion d'information à modifier."},
                    status=http_status.HTTP_404_NOT_FOUND,
                )
            serializer = ReunionInformationSerializer(ri, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        if request.method == 'DELETE':
            if not ri:
                return Response(
                    {"detail": "Aucune réunion d'information à supprimer."},
                    status=http_status.HTTP_404_NOT_FOUND,
                )
            ri.delete()
            return Response(status=http_status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='candidats', permission_classes=[permissions.IsAuthenticated])
    def candidats(self, request, pk=None):
        """
        Liste tous les candidats de cette campagne avec les détails de leur convocation RI si existante.
        """
        campagne = self.get_object()
        candidatures = (
            campagne.candidatures.all()
            .prefetch_related("convocations_ri__creneau")
            .order_by("-date_soumission")
        )
        from candidature.serializers import CampagneCandidatSerializer
        serializer = CampagneCandidatSerializer(candidatures, many=True)
        return Response(serializer.data)


class ReunionInformationViewSet(viewsets.ModelViewSet):
    queryset = ReunionInformation.objects.all()
    serializer_class = ReunionInformationSerializer
    permission_classes = [permissions.IsAuthenticated, HasRole.with_roles(User.Role.ADMIN)()]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'creneaux', 'convocations', 'presence', 'stats']:
            if self.action in ['creneaux', 'stats', 'convocations'] and self.request.method == 'GET':
                return [permissions.IsAuthenticated()]
            return [permissions.IsAuthenticated(), IsAdministrateur()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=['get', 'post'], url_path='creneaux')
    def creneaux(self, request, pk=None):
        reunion = self.get_object()
        
        if request.method == 'GET':
            creneaux = reunion.creneaux.all()
            serializer = CreneauRISerializer(creneaux, many=True)
            return Response(serializer.data)
        
        if request.method == 'POST':
            serializer = CreneauRISerializer(data=request.data, context={'reunion': reunion})
            serializer.is_valid(raise_exception=True)
            serializer.save(reunion=reunion)
            return Response(serializer.data, status=http_status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post'], url_path='convocations')
    def convocations(self, request, pk=None):
        """
        GET: Liste des convocations RI de cette réunion (filtrable par creneau ou statut).
        POST: Création / envoi en lot de convocations pour les candidature_ids indiqués.
        """
        reunion = self.get_object()

        if request.method == 'GET':
            from candidature.models import ConvocationRI
            from candidature.serializers import ConvocationRISerializer
            
            qs = ConvocationRI.objects.filter(reunion_information=reunion).select_related(
                "candidature", "creneau", "reunion_information"
            )

            creneau_id = request.query_params.get("creneau")
            statut = request.query_params.get("statut")
            search = request.query_params.get("search")

            if creneau_id:
                qs = qs.filter(creneau_id=creneau_id)
            if statut:
                qs = qs.filter(statut=statut)
            if search:
                qs = qs.filter(
                    candidature__nom__icontains=search
                ) | qs.filter(
                    candidature__prenom__icontains=search
                ) | qs.filter(
                    candidature__email__icontains=search
                )

            serializer = ConvocationRISerializer(qs, many=True)
            return Response(serializer.data)

        if request.method == 'POST':
            from candidature.serializers import ConvocationRICreateBatchSerializer, ConvocationRISerializer
            from candidature.services.convocation_service import creer_convocations_ri_en_lot

            serializer = ConvocationRICreateBatchSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            candidature_ids = serializer.validated_data["candidature_ids"]
            creneau_id = serializer.validated_data.get("creneau_id")
            envoyer_email = serializer.validated_data.get("envoyer_email", True)

            result = creer_convocations_ri_en_lot(
                reunion_information=reunion,
                candidature_ids=candidature_ids,
                creneau_id=creneau_id,
                send_email=envoyer_email,
            )

            convocations_data = ConvocationRISerializer(result["convocations"], many=True).data

            return Response({
                "success": True,
                "message": f"{result['total']} convocation(s) traitée(s), {result['envoyes']} email(s) envoyé(s).",
                "total": result["total"],
                "envoyes": result["envoyes"],
                "convocations": convocations_data,
            }, status=http_status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='presence')
    def presence(self, request, pk=None):
        """
        Point d'entrée du scanner Webcam / QR code pour enregistrer la présence à cette RI.
        """
        reunion = self.get_object()
        from candidature.serializers import ScanQRSerializer
        from candidature.services.presence_service import valider_presence_par_qr

        serializer = ScanQRSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        result = valider_presence_par_qr(
            qr_token_str=token,
            reunion_id=reunion.id,
            campagne_id=reunion.campagne_id,
        )
        return Response(result, status=http_status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='stats')
    def stats(self, request, pk=None):
        """
        Statistiques complètes de la RI : total, présents, absents, ventilation par créneau et historique récent.
        """
        reunion = self.get_object()
        from candidature.models import ConvocationRI

        qs = ConvocationRI.objects.filter(reunion_information=reunion)

        total_convoques = qs.count()
        presents = qs.filter(statut=ConvocationRI.StatutPresence.PRESENT).count()
        absents = qs.filter(statut=ConvocationRI.StatutPresence.ABSENT).count()

        # Détails par créneau
        creneaux_stats = []
        for cr in reunion.creneaux.all():
            cr_qs = qs.filter(creneau=cr)
            creneaux_stats.append({
                "id": cr.id,
                "nom": cr.nom or "Créneau",
                "heure_debut": str(cr.heure_debut)[:5],
                "heure_fin": str(cr.heure_fin)[:5] if cr.heure_fin else "",
                "capacite": cr.capacite,
                "total": cr_qs.count(),
                "presents": cr_qs.filter(statut=ConvocationRI.StatutPresence.PRESENT).count(),
                "absents": cr_qs.filter(statut=ConvocationRI.StatutPresence.ABSENT).count(),
            })

        # Historique des derniers scans
        derniers_scans = (
            qs.filter(statut=ConvocationRI.StatutPresence.PRESENT, date_presence__isnull=False)
            .select_related("candidature", "creneau")
            .order_by("-date_presence")[:30]
        )

        historique = [
            {
                "id": c.id,
                "candidature_id": c.candidature_id,
                "nom": c.candidature.nom,
                "prenom": c.candidature.prenom,
                "email": c.candidature.email,
                "telephone": c.candidature.telephone,
                "creneau": (c.creneau.nom or f"{str(c.creneau.heure_debut)[:5]} - {str(c.creneau.heure_fin)[:5]}") if c.creneau else "Standard",
                "date_presence": c.date_presence.isoformat() if c.date_presence else None,
                "statut": c.statut,
            }
            for c in derniers_scans
        ]

        return Response({
            "total": total_convoques,
            "present": presents,
            "absent": absents,
            "creneaux": creneaux_stats,
            "historique": historique,
        })


class CreneauRIViewSet(viewsets.ModelViewSet):
    queryset = CreneauRI.objects.all()
    serializer_class = CreneauRISerializer
    permission_classes = [permissions.IsAuthenticated, HasRole.with_roles(User.Role.ADMIN)()]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdministrateur()]
        return [permissions.IsAuthenticated()]

