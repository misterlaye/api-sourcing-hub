from django.http import HttpResponse
from rest_framework import viewsets, mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Candidature, Convocation
from .serializers import (
    CandidatureSerializer,
    CandidatureCreateSerializer,
    ConvocationSerializer,
    ConvocationCreateSerializer,
    ScanQRSerializer,
)
from .services import (
    valider_presence_par_qr,
    generate_convocation_pdf,
    send_convocation_email,
)


class CandidatureCreateViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Endpoint public de création d'une candidature."""
    queryset = Candidature.objects.all()
    serializer_class = CandidatureCreateSerializer
    permission_classes = [permissions.AllowAny]


class CandidatureAdminViewSet(viewsets.ModelViewSet):
    """Endpoint réservé à l'administration pour gérer les candidatures."""
    queryset = Candidature.objects.select_related("campagne").all()
    serializer_class = CandidatureSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        campagne_id = self.request.query_params.get("campagne")
        if campagne_id:
            queryset = queryset.filter(campagne_id=campagne_id)
        return queryset


class ConvocationViewSet(viewsets.ModelViewSet):
    """
    ViewSet d'administration pour la gestion des convocations et du scan QR code.
    Accessible uniquement aux administrateurs authentifiés.
    """
    queryset = Convocation.objects.select_related("candidature", "campagne").all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return ConvocationCreateSerializer
        return ConvocationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        campagne_id = self.request.query_params.get("campagne")
        type_convocation = self.request.query_params.get("type")
        statut = self.request.query_params.get("statut")
        candidature_id = self.request.query_params.get("candidature")

        if campagne_id:
            queryset = queryset.filter(campagne_id=campagne_id)
        if type_convocation:
            queryset = queryset.filter(type=type_convocation)
        if statut:
            queryset = queryset.filter(statut=statut)
        if candidature_id:
            queryset = queryset.filter(candidature_id=candidature_id)

        return queryset

    @action(detail=False, methods=["post"], url_path="scan-qr", permission_classes=[permissions.IsAuthenticated])
    def scan_qr(self, request):
        """
        Point d'entrée du scanner Webcam Admin.
        Reçoit le QR token et valide la présence du candidat côté backend.
        """
        serializer = ScanQRSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qr_token = serializer.validated_data["qr_token"]
        campagne_id = serializer.validated_data.get("campagne")

        result = valider_presence_par_qr(qr_token, campagne_id=campagne_id)
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="presences", permission_classes=[permissions.IsAuthenticated])
    def presences(self, request):
        """
        Retourne les statistiques de présence et l'historique des scans pour une campagne donnée.
        """
        campagne_id = request.query_params.get("campagne")
        qs = Convocation.objects.filter(type=Convocation.Type.RI)

        if campagne_id:
            qs = qs.filter(campagne_id=campagne_id)

        total_convoques = qs.count()
        presents = qs.filter(statut=Convocation.Statut.PRESENT).count()
        en_attente = qs.filter(statut=Convocation.Statut.EN_ATTENTE).count()

        # Historique des scans récents (ordonnés par heure de présence)
        derniers_scans = (
            qs.filter(statut=Convocation.Statut.PRESENT, presence_at__isnull=False)
            .select_related("candidature")
            .order_by("-presence_at")[:20]
        )

        historique = [
            {
                "id": c.id,
                "candidature_id": c.candidature_id,
                "nom": c.candidature.nom,
                "prenom": c.candidature.prenom,
                "email": c.candidature.email,
                "presence_at": c.presence_at.isoformat() if c.presence_at else None,
                "statut": c.statut,
            }
            for c in derniers_scans
        ]

        return Response({
            "total_convoques": total_convoques,
            "presents": presents,
            "en_attente": en_attente,
            "historique": historique,
        })

    @action(detail=True, methods=["get"], url_path="pdf", permission_classes=[permissions.IsAuthenticated])
    def telecharger_pdf(self, request, pk=None):
        """Télécharge directement le document PDF officiel de convocation avec QR code."""
        convocation = self.get_object()
        pdf_bytes = generate_convocation_pdf(convocation)
        filename = f"Convocation_{convocation.type}_{convocation.candidature.nom}_{convocation.candidature.prenom}.pdf"
        filename = filename.replace(" ", "_")

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=["post"], url_path="renvoyer-email", permission_classes=[permissions.IsAuthenticated])
    def renvoyer_email(self, request, pk=None):
        """Renvoie l'email de convocation avec le PDF en pièce jointe."""
        convocation = self.get_object()
        success = send_convocation_email(convocation)
        if success:
            return Response({"success": True, "message": "Email envoyé avec succès."})
        return Response({"success": False, "message": "Erreur lors de l'envoi de l'email."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CandidateConvocationsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espace candidat : permet au candidat connecté de consulter ses prochaines convocations
    d'entretiens (Technique, Motivation, Final) après sa validation à la RI.
    """
    serializer_class = ConvocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_email = self.request.user.email
        qs = Convocation.objects.filter(
            candidature__email=user_email
        ).exclude(type=Convocation.Type.RI)

        type_conv = self.request.query_params.get("type")
        if type_conv:
            qs = qs.filter(type=type_conv)

        return qs.order_by("date", "heure_debut")


class ConvocationRIViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour la consultation, le téléchargement de PDF, le renvoi d'email et
    l'accès public sans compte aux convocations RI via token.
    """
    from .models import ConvocationRI
    from .serializers import ConvocationRISerializer

    queryset = ConvocationRI.objects.select_related("candidature", "creneau", "reunion_information").all()
    serializer_class = ConvocationRISerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["get"], url_path="pdf", permission_classes=[permissions.IsAuthenticated])
    def telecharger_pdf(self, request, pk=None):
        """Télécharge directement le document PDF officiel de convocation RI avec QR code."""
        convocation = self.get_object()
        pdf_bytes = generate_convocation_pdf(convocation)
        filename = f"Convocation_RI_{convocation.candidature.nom}_{convocation.candidature.prenom}.pdf"
        filename = filename.replace(" ", "_")

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=["post"], url_path="renvoyer-email", permission_classes=[permissions.IsAuthenticated])
    def renvoyer_email(self, request, pk=None):
        """Renvoie l'email de convocation RI avec le PDF en pièce jointe."""
        from django.utils import timezone
        convocation = self.get_object()
        success = send_convocation_email(convocation)
        if success:
            convocation.date_envoi = timezone.now()
            convocation.save(update_fields=["date_envoi"])
            return Response({"success": True, "message": "Email envoyé avec succès."})
        return Response(
            {"success": False, "message": "Erreur lors de l'envoi de l'email."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    @action(detail=False, methods=["get"], url_path="public/(?P<token>[^/.]+)", permission_classes=[permissions.AllowAny])
    def public_view(self, request, token=None):
        """
        Consultation publique de sa convocation RI par le candidat sans avoir besoin de compte.
        """
        import uuid
        from .models import ConvocationRI
        from .serializers import ConvocationRISerializer
        from .services.qr_code_service import generate_qr_code_base64

        try:
            token_uuid = uuid.UUID(str(token).strip())
        except (ValueError, AttributeError):
            return Response({"detail": "Token de convocation invalide."}, status=status.HTTP_404_NOT_FOUND)

        convocation = ConvocationRI.objects.select_related(
            "candidature", "creneau", "reunion_information", "reunion_information__campagne"
        ).filter(token=token_uuid).first()

        if not convocation:
            return Response({"detail": "Convocation introuvable."}, status=status.HTTP_404_NOT_FOUND)

        data = ConvocationRISerializer(convocation).data
        data["qr_code_base64"] = generate_qr_code_base64(convocation.token)
        return Response(data)