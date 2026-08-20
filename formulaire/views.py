from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import render
from django.db import transaction
from django.db import IntegrityError

# Create your views here.
from rest_framework import status , viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .models import Formulaire, SectionFormulaire, Question, OptionQuestion, ReponseQuestion, ReponseOption
from .serializers import FormulaireSerializer, FormulairePreviewSerializer, SectionFormulaireSerializer, QuestionSerializer, OptionQuestionSerializer, ReponseSubmissionSerializer, ReponseQuestionSerializer, ReponseCandidatureSerializer, ReponseOptionSerializer, MesReponsesSerializer, FormulaireWriteSerializer
from .permissions import IsAdministrateur
from .services import publier_formulaire,depublier_formulaire
from candidature.models import Candidature

from .models import (
    Formulaire,
    OptionQuestion,
    Question,
    ReponseOption,
    ReponseQuestion,
    SectionFormulaire,
)
from .permissions import IsAdministrateur
from .serializers import (
    FormulairePreviewSerializer,
    FormulaireSerializer,
    OptionQuestionSerializer,
    QuestionSerializer,
    ReponseCandidatureSerializer,
    ReponseOptionSerializer,
    ReponseQuestionSerializer,
    ReponseSubmissionSerializer,
    SectionFormulaireSerializer,
)
from .services import depublier_formulaire, publier_formulaire


class FormulaireViewSet(viewsets.ModelViewSet):
    """
    API de gestion des formulaires liés aux campagnes.
    
    RÈGLE MÉTIER IMPORTANTE :
    - L'administration des formulaires (création, édition, publication) est réservée aux administrateurs connectés.
    - La consultation et la soumission d'un formulaire PUBLIÉ sont entièrement PUBLIQUES (AllowAny).
      Aucune connexion ni JWT n'est requis pour qu'un candidat consulte ou soumette le formulaire.
    - La création du compte utilisateur n'intervient pas ici : seule une Candidature avec statut EN_ATTENTE
      est créée. Le compte utilisateur ne sera créé/invité qu'après la réunion d'information.
    """
    serializer_class = FormulaireSerializer

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return FormulaireWriteSerializer
        return FormulaireSerializer

    def get_permissions(self):
        # Opérations d'administration réservées à l'administrateur
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'publier', 'depublier']:
            return [permissions.IsAuthenticated(), IsAdministrateur()]
        # Consultation publique et soumission ouvertes à tous sans authentification
        if self.action in ['retrieve', 'public', 'soumettre']:
            return [permissions.AllowAny()]
        # Liste et prévisualisation admin réservées aux utilisateurs connectés
        return [permissions.IsAuthenticated()]

    def retrieve(self, request, *args, **kwargs):
        """
        Consultation d'un formulaire :
        - Accessible publiquement si le formulaire est publié et actif.
        - Les administrateurs connectés peuvent consulter même en mode brouillon.
        """
        instance = self.get_object()
        if not (request.user and request.user.is_authenticated):
            if not instance.publier or not instance.actif:
                return Response(
                    {"detail": "Ce formulaire n'est pas accessible au public ou n'est plus actif."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {"detail": "Un formulaire existe déjà pour cette campagne."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get_queryset(self):
        return Formulaire.objects.select_related("campagne").prefetch_related(
            Prefetch(
                "sections",
                queryset=SectionFormulaire.objects.order_by("ordre", "id").prefetch_related(
                    Prefetch(
                        "questions",
                        queryset=Question.objects.order_by("ordre", "id").prefetch_related("options"),
                    )
                ),
            )
        )
    def get_permissions(self):
        # les Operateur sont revervees au administrateur
        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
            "publier",
            "depublier",
        ] :
            return [
                IsAdministrateur(),
                permissions.IsAuthenticated(),
            ]
        # Les opérations de lecture nécessitent
        # seulement une authentification.
        return [
            permissions.IsAuthenticated(),
        ]
    def perform_create(self, serializer):
        campagne = serializer.validated_data["campagne"]
        if hasattr(campagne, "formulaire"):
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                "campagne": "Cette campagne possède déjà un formulaire."
            })
        serializer.save()

    @extend_schema(
        summary="Prévisualiser un formulaire",
        description="Retourner le formulaire complet pour le mode visualisation.",
        responses=FormulairePreviewSerializer,
    )
    @action(detail=True, methods=["get"], url_path="preview")
    def preview(self, request, pk=None):
        formulaire = self.get_object()
        serializer = FormulairePreviewSerializer(formulaire)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Accès public à un formulaire publié",
        description="Permet à tout candidat sans authentification de charger le formulaire publié.",
        responses=FormulaireSerializer,
    )
    @action(detail=True, methods=["get"], url_path="public", permission_classes=[permissions.AllowAny])
    def public(self, request, pk=None):
        formulaire = self.get_object()
        if not formulaire.publier or not formulaire.actif:
            return Response(
                {"detail": "Ce formulaire n'est pas publié ou est désactivé."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(formulaire)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Publier un formulaire",
        description="Publie le formulaire après vérification de sa structure.",
        responses=FormulaireSerializer,
    )
    @action(detail=True, methods=["post"], url_path="publier")
    def publier(self, request, pk=None):
        formulaire_obj = self.get_object()
        try:
            formulaire_obj = publier_formulaire(formulaire_obj)
        except ValueError as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(formulaire_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Dépublier un formulaire",
        description="Désactiver la publication du formulaire",
        responses=FormulaireSerializer,
    )
    @action(detail=True, methods=["post"], url_path="depublier")
    def depublier(self, request, pk=None):
        formulaire_obj = self.get_object()
        formulaire_obj = depublier_formulaire(formulaire_obj)
        serializer = self.get_serializer(formulaire_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Soumettre les réponses d'un formulaire (Public ou Authentifié)",
        description=(
            "Enregistre les réponses et crée/met à jour la Candidature avec le statut EN_ATTENTE. "
            "Accessible publiquement sans connexion ni token JWT."
        ),
        request=ReponseSubmissionSerializer,
        responses=MesReponsesSerializer,
    )
    @action(detail=True, methods=["post"], url_path="soumettre", permission_classes=[permissions.AllowAny])
    def soumettre(self, request, pk=None):
        formulaire = self.get_object()

        if not formulaire.publier:
            return Response(
                {"detail": "Ce formulaire n'est pas publié."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not formulaire.actif:
            return Response(
                {"detail": "Ce formulaire est désactivé."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReponseSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reponses_data = serializer.validated_data["reponses"]

        # -------------------------------------------------------------
        # Extraction des informations d'identité du candidat :
        # 1. Depuis les champs racine de request.data
        # 2. Depuis les réponses fournies (questions de type EMAIL, ou texte)
        # 3. Depuis l'utilisateur connecté si présent
        # -------------------------------------------------------------
        nom = (request.data.get("nom") or "").strip()
        prenom = (request.data.get("prenom") or "").strip()
        email = (request.data.get("email") or "").strip()
        telephone = (request.data.get("telephone") or "").strip()

        for r_item in reponses_data:
            q = r_item["question"]
            val = (r_item.get("valeur") or "").strip()
            if not email and q.type_question == Question.TypeQuestion.EMAIL and val:
                email = val
            q_lower = q.texte.lower()
            if not nom and ("nom" in q_lower and "prénom" not in q_lower and "prenom" not in q_lower) and val:
                nom = val
            if not prenom and ("prénom" in q_lower or "prenom" in q_lower) and val:
                prenom = val
            if not telephone and ("téléphone" in q_lower or "telephone" in q_lower or "tel" in q_lower) and val:
                telephone = val

        if not email and request.user and request.user.is_authenticated:
            email = request.user.email
            if not nom:
                nom = getattr(request.user, "last_name", "")
            if not prenom:
                prenom = getattr(request.user, "first_name", "")
            if not telephone:
                telephone = getattr(request.user, "phone_number", "")

        if not email:
            return Response(
                {"detail": "Une adresse email est obligatoire pour enregistrer votre candidature."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not nom:
            nom = email.split("@")[0]

        # -------------------------------------------------------------
        # Création ou mise à jour de la candidature avec statut EN_ATTENTE
        # Aucun compte utilisateur n'est créé à cette étape.
        # -------------------------------------------------------------
        candidature, created = Candidature.objects.get_or_create(
            email=email,
            campagne=formulaire.campagne,
            defaults={
                "nom": nom,
                "prenom": prenom,
                "telephone": telephone,
                "status": Candidature.Status.EN_ATTENTE,
            },
        )
        if not created:
            candidature.nom = nom or candidature.nom
            candidature.prenom = prenom or candidature.prenom
            candidature.telephone = telephone or candidature.telephone
            candidature.status = Candidature.Status.EN_ATTENTE
            candidature.save()

        questions_formulaire = set(
            Question.objects.filter(section__formulaire=formulaire).values_list("id", flat=True)
        )

        types_avec_options = [
            Question.TypeQuestion.RADIO,
            Question.TypeQuestion.CHECKBOX,
            Question.TypeQuestion.SELECT,
        ]

        for reponse_data in reponses_data:
            question = reponse_data["question"]

            if question.id not in questions_formulaire:
                return Response(
                    {"detail": f"La question {question.id} n'appartient pas à ce formulaire."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if question.type_question in types_avec_options:
                options = reponse_data.get("options", [])

                if question.type_question == Question.TypeQuestion.CHECKBOX:
                    if question.obligatoire and not options:
                        return Response(
                            {"detail": f"La question {question.id} est obligatoire."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    for option in options:
                        if option.question_id != question.id:
                            return Response(
                                {"detail": f"L'option {option.id} n'appartient pas à la question {question.id}."},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                else:
                    if question.obligatoire and not options:
                        return Response(
                            {"detail": f"La question {question.id} est obligatoire."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    if len(options) != 1:
                        return Response(
                            {"detail": f"La question {question.id} nécessite exactement une option."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    option = options[0]
                    if option.question_id != question.id:
                        return Response(
                            {"detail": f"L'option {option.id} n'appartient pas à la question {question.id}."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
            else:
                valeur = reponse_data.get("valeur", "")
                if question.obligatoire and not valeur.strip():
                    return Response(
                        {"detail": f"La question {question.id} est obligatoire."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if valeur.strip():
                    if question.type_question == Question.TypeQuestion.YES_NO:
                        if valeur.strip() not in ["Oui", "Non"]:
                            return Response(
                                {"detail": f"La question {question.id} attend 'Oui' ou 'Non'."},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                    elif question.type_question == Question.TypeQuestion.NUMBER:
                        try:
                            float(valeur)
                        except (TypeError, ValueError):
                            return Response(
                                {"detail": f"La question {question.id} attend un nombre valide."},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                    elif question.type_question == Question.TypeQuestion.EMAIL:
                        from django.core.validators import validate_email
                        from django.core.exceptions import ValidationError
                        try:
                            validate_email(valeur)
                        except ValidationError:
                            return Response(
                                {"detail": f"La question {question.id} attend un email valide."},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                    elif question.type_question == Question.TypeQuestion.DATE:
                        from datetime import datetime
                        try:
                            datetime.strptime(valeur, "%Y-%m-%d")
                        except ValueError:
                            return Response(
                                {"detail": f"La question {question.id} attend une date valide (AAAA-MM-JJ)."},
                                status=status.HTTP_400_BAD_REQUEST,
                            )

        try:
            with transaction.atomic():
                result_reponses = []
                for reponse_data in reponses_data:
                    question = reponse_data["question"]

                    if question.type_question in types_avec_options:
                        options = reponse_data.get("options", [])

                        if question.type_question == Question.TypeQuestion.CHECKBOX:
                            reponse_question, _ = ReponseQuestion.objects.update_or_create(
                                candidature=candidature,
                                question=question,
                                defaults={"valeur": ""},
                            )
                            reponse_question.options_selectionnees.all().delete()
                            for option in options:
                                ReponseOption.objects.create(reponse=reponse_question, option=option)
                        else:
                            option = options[0]
                            reponse_question, _ = ReponseQuestion.objects.update_or_create(
                                candidature=candidature,
                                question=question,
                                defaults={"valeur": option.valeur},
                            )
                            reponse_question.options_selectionnees.all().delete()
                            ReponseOption.objects.create(reponse=reponse_question, option=option)
                    else:
                        valeur = reponse_data.get("valeur", "")
                        reponse_question, _ = ReponseQuestion.objects.update_or_create(
                            candidature=candidature,
                            question=question,
                            defaults={"valeur": valeur},
                        )

                    result_reponses.append(reponse_question)

            output_serializer = MesReponsesSerializer({
                "reponses": result_reponses,
            })
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        summary="Mes réponses",
        description="Retourne les réponses du candidat connecté pour ce formulaire.",
        responses=MesReponsesSerializer,
    )
    @action(detail=True, methods=["get"], url_path="mes-reponses",)
    def mes_reponses(self, request, pk=None):
        formulaire = self.get_object()

        candidature = Candidature.objects.filter(
            email=request.user.email,
            campagne=formulaire.campagne
        ).first()

        if not candidature:
            return Response(
                {"detail": "Aucune candidature trouvée pour cet utilisateur."},
                status=status.HTTP_404_NOT_FOUND,
            )

        reponses = ReponseQuestion.objects.filter(
            candidature=candidature,
            question__section__formulaire=formulaire
        ).select_related("question").prefetch_related("options_selectionnees__option")

        serializer = MesReponsesSerializer({
            "reponses": reponses,
        })
        return Response(serializer.data, status=status.HTTP_200_OK)


class CandidatureReponsesView(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, IsAdministrateur]

    def list(self, request, candidature_id=None):
        try:
            candidature = Candidature.objects.get(id=candidature_id)
        except Candidature.DoesNotExist:
            return Response(
                {"detail": "Candidature introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        reponses = ReponseQuestion.objects.filter(candidature=candidature).select_related("question").prefetch_related("options_selectionnees__option")
        serializer = ReponseCandidatureSerializer({
            "candidature": candidature.id,
            "reponses": reponses,
        })
        return Response(serializer.data, status=status.HTTP_200_OK)


class SectionFormulaireViewSet(viewsets.ModelViewSet):
    # API pour la gestion des sections
    serializer_class= SectionFormulaireSerializer
    def get_queryset(self):
        """
        Permet de récupérer les sections d'un formulaire.

        Exemple :

        /api/sections/?formulaire=1
        """
        queryset = SectionFormulaire.objects.prefetch_related("questions__options")
        formulaire_id = (self.request.query_params.get( "formulaire" )
        )
        if formulaire_id:
            queryset = queryset.filter(
                formulaire_id=formulaire_id
            )
        return queryset
    def get_permissions(self):
        # Pour modifier une section,
        # l'utilisateur doit être administrateur.
        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
        ]:
            return [
                permissions.IsAuthenticated(),
                IsAdministrateur(),
            ]

        return [
            permissions.IsAuthenticated(),
        ]    
class QuestionViewSet(viewsets.ModelViewSet):
    #API de gestion des questions.
    serializer_class = QuestionSerializer
    def get_queryset(self):
        """
        Permet de filtrer les questions par section.

        Exemple :

        /api/questions/?section=1
        """
        queryset = (  Question.objects  .prefetch_related("options"))
        section_id = ( self.request.query_params.get(  "section" )
        )
        if section_id:
            queryset = queryset.filter(
                section_id=section_id
            )
        return queryset
    def get_permissions(self):
        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
        ]:
            return [
                permissions.IsAuthenticated(),
                IsAdministrateur(),
            ]

        return [
            permissions.IsAuthenticated(),
        ]
class OptionQuestionViewSet(viewsets.ModelViewSet):
    #API de gestion des options des questions.
    serializer_class = OptionQuestionSerializer
    def get_queryset(self):
        """
        Permet de filtrer les options par question.

        Exemple :

        /api/options/?question=1
        """
        queryset = OptionQuestion.objects.all()
        question_id = ( self.request.query_params.get("question")
        )
        if question_id:
            queryset = queryset.filter(
                question_id=question_id
            )
        return queryset
    def get_permissions(self):
        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
        ]:
            return [
                permissions.IsAuthenticated(),
                IsAdministrateur(),
            ]

        return [
            permissions.IsAuthenticated(),
        ]


class ReponseQuestionViewSet(viewsets.ModelViewSet):
    queryset = ReponseQuestion.objects.all()
    serializer_class = ReponseQuestionSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsAdministrateur()]
        return [permissions.IsAuthenticated()]


class ReponseOptionViewSet(viewsets.ModelViewSet):
    queryset = ReponseOption.objects.all()
    serializer_class = ReponseOptionSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsAdministrateur()]
        return [permissions.IsAuthenticated()]
