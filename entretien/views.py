from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from accounts.permissions import HasRole
from accounts.models import User
from formulaire.permissions import IsAdministrateur
from .models import Entretien, CreneauEntretien, ConvocationEntretien
from .serializers import (
    EntretienSerializer,
    CreneauEntretienSerializer,
    ConvocationEntretienSerializer,
    ConfirmationEntretienSerializer,
)
from .services import (
    confirmer_et_envoyer_convocations,
    envoyer_email_convocation_candidat,
)


class EntretienViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion complète du cycle de vie des sessions d'entretiens.
    Permet la planification, la gestion des jurys/créneaux et la confirmation
    avec déclenchement automatique des convocations et plannings.
    """
    queryset = (
        Entretien.objects.select_related("campagne")
        .prefetch_related("jurys", "creneaux__candidature", "creneaux__jurys")
        .all()
    )
    serializer_class = EntretienSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "confirmer_et_convoquer"]:
            return [permissions.IsAuthenticated(), IsAdministrateur()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        campagne_id = self.request.query_params.get("campagne")
        type_entretien = self.request.query_params.get("type")
        statut = self.request.query_params.get("statut")
        date = self.request.query_params.get("date")

        if campagne_id:
            queryset = queryset.filter(campagne_id=campagne_id)
        if type_entretien:
            queryset = queryset.filter(type=type_entretien)
        if statut:
            queryset = queryset.filter(statut=statut)
        if date:
            queryset = queryset.filter(date=date)

        return queryset

    @extend_schema(
        request=ConfirmationEntretienSerializer,
        responses={200: ConvocationEntretienSerializer(many=True)},
        description="Valide la session, crée les ConvocationEntretien, passe le statut à CONFIRME et envoie les emails aux candidats et jurys."
    )
    @action(detail=True, methods=["post"], url_path="confirmer-et-convoquer")
    def confirmer_et_convoquer(self, request, pk=None):
        """
        Action principale : Confirmer et envoyer les convocations.
        Règles métier :
        - Récupère les créneaux, jurys et candidats déjà planifiés.
        - Vérifie que chaque candidat possède un créneau et qu'au moins un jury est affecté.
        - Crée les ConvocationEntretien.
        - Passe le statut de l'entretien à CONFIRME.
        - Envoie une convocation à chaque candidat.
        - Envoie le planning complet aux jurys.
        """
        entretien = self.get_object()

        serializer = ConfirmationEntretienSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        envoyer_emails = serializer.validated_data.get("envoyer_emails", True)

        try:
            result = confirmer_et_envoyer_convocations(
                entretien=entretien,
                envoyer_emails=envoyer_emails,
            )
        except DjangoValidationError as e:
            return Response(
                {
                    "success": False,
                    "error": "Validation de planification échouée",
                    "details": e.messages if hasattr(e, "messages") else [str(e)],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": "Une erreur est survenue lors de la confirmation",
                    "details": [str(e)],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        convocations_data = ConvocationEntretienSerializer(
            result["convocations"], many=True
        ).data

        return Response(
            {
                "success": True,
                "message": f"Session confirmée avec succès. {result['total_candidats']} convocation(s) émise(s), {result['emails_candidats_envoyes']} email(s) candidat(s) et {result['emails_jurys_envoyes']} planning(s) jury envoyés.",
                "statut": result["statut"],
                "total_candidats": result["total_candidats"],
                "emails_candidats_envoyes": result["emails_candidats_envoyes"],
                "total_jurys": result["total_jurys"],
                "emails_jurys_envoyes": result["emails_jurys_envoyes"],
                "convocations": convocations_data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="planning-jurys")
    def planning_jurys(self, request, pk=None):
        """Retourne le planning complet de la session structuré par membre du jury."""
        entretien = self.get_object()
        creneaux = (
            entretien.creneaux.select_related("candidature")
            .prefetch_related("jurys")
            .filter(candidature__isnull=False)
            .order_by("heure_debut")
        )

        session_jurys = set(entretien.jurys.all())
        all_jurys = set(session_jurys)
        for c in creneaux:
            all_jurys.update(c.jurys.all())

        planning = []
        for jury in all_jurys:
            jury_creneaux = [
                c for c in creneaux
                if jury in (list(c.jurys.all()) or list(session_jurys))
            ]
            planning.append({
                "jury": {
                    "id": jury.id,
                    "email": jury.email,
                    "name": f"{jury.first_name} {jury.last_name}".strip() or jury.email,
                    "role": jury.role,
                },
                "total_passages": len(jury_creneaux),
                "creneaux": CreneauEntretienSerializer(jury_creneaux, many=True).data,
            })

        return Response({
            "entretien_id": entretien.id,
            "campagne": entretien.campagne.title,
            "type": entretien.type,
            "date": entretien.date,
            "planning": planning,
        })


class CreneauEntretienViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion granulaire des créneaux horaires d'entretiens."""
    queryset = (
        CreneauEntretien.objects.select_related("entretien", "candidature")
        .prefetch_related("jurys")
        .all()
    )
    serializer_class = CreneauEntretienSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdministrateur()]

    def get_queryset(self):
        queryset = super().get_queryset()
        entretien_id = self.request.query_params.get("entretien")
        if entretien_id:
            queryset = queryset.filter(entretien_id=entretien_id)
        return queryset


class ConvocationEntretienViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de consultation des convocations officielles aux entretiens."""
    queryset = (
        ConvocationEntretien.objects.select_related(
            "entretien", "entretien__campagne", "candidature", "creneau"
        ).all()
    )
    serializer_class = ConvocationEntretienSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        entretien_id = self.request.query_params.get("entretien")
        candidature_id = self.request.query_params.get("candidature")
        statut = self.request.query_params.get("statut")
        type_entretien = self.request.query_params.get("type")

        if entretien_id:
            queryset = queryset.filter(entretien_id=entretien_id)
        if candidature_id:
            queryset = queryset.filter(candidature_id=candidature_id)
        if statut:
            queryset = queryset.filter(statut=statut)
        if type_entretien:
            queryset = queryset.filter(type=type_entretien)

        return queryset

    @action(detail=True, methods=["post"], url_path="renvoyer-email", permission_classes=[permissions.IsAuthenticated, IsAdministrateur()])
    def renvoyer_email(self, request, pk=None):
        """Renvoie manuellement l'email officiel de convocation au candidat."""
        from django.utils import timezone
        convocation = self.get_object()
        success = envoyer_email_convocation_candidat(convocation)
        if success:
            convocation.date_envoi = timezone.now()
            convocation.save(update_fields=["date_envoi", "date_modification"])
            return Response({"success": True, "message": "Email de convocation renvoyé avec succès."})
        return Response(
            {"success": False, "message": "Erreur lors de l'envoi de l'email."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class MesConvocationsEntretienViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espace candidat : permet à tout candidat connecté de consulter en temps réel
    ses convocations aux entretiens (Technique, Motivation, Final).
    """
    serializer_class = ConvocationEntretienSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_email = self.request.user.email
        return (
            ConvocationEntretien.objects.select_related(
                "entretien", "entretien__campagne", "candidature", "creneau"
            )
            .filter(candidature__email=user_email)
            .order_by("date", "heure_debut")
        )
