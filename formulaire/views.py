from django.db import transaction
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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
    # Api permet de gere les formulaire et le formulaire est lie a une campagne
    serializer_class= FormulaireSerializer
    def get_queryset(self):
        #recupere les formlaires avec leus sections , options etc
        # Cela évite de multiplier inutilement les requêtes
        #SQL lorsque Vue.js demande un formulaire complet. 
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
        # On vérifie qu'une campagne n'a pas déjà  un formulaire.
        campagne= serializer.validated_data["campagne"]
        # Comme Campagne -> Formulaire est OneToOne,
        # une campagne ne peut avoir qu'un formulaire.
        if hasattr(campagne,"formulaire"):
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                "campagne":("cette campagne possede deja un formulaire")
            })
        serializer.save()
    @extend_schema(
        summary="Previsualiser un formulaire",
        description=("Retouner le formulaire complet pour le mode visualisation."),
        responses= FormulairePreviewSerializer,

    )
    @action(detail=True, methods=["get"],url_path="preview",)
    def preview(self, request,pk=None):
        #Cette route est utilisée lorsque l'administrateur
        #clique sur l'icône 
        formulaire=self.get_object()
        serializer= FormulairePreviewSerializer(formulaire)
        return Response(serializer.data, status=status.HTTP_200_OK,)
    @extend_schema(
        summary="Publier un formulaire",
        description=( "Publie le formulaire après vérification "
                    "de sa structure."),
        responses=FormulaireSerializer,
    )

    @action(detail=True,methods=["post"],url_path="publier",)
    def publier(self,request,pk=None):
        Formulaire= self.get_object()
        try:
            formulaire=publier_formulaire(Formulaire)
        except ValueError as error:
            return Response(

                {
                    "detail": str(error)
                },
                status=status.HTTP_400_BAD_REQUEST ,
            )
        serializer= self.get_serializer(formulaire)
        return Response(serializer.data, status=status.HTTP_200_OK,)
    @extend_schema(
        summary="Dépublier un formulaire",
        description="Deactiver la publication du formulaire",
        responses=FormulaireSerializer,
    )
    @action(detail=True,methods=["post"],url_path="depublier",)
    def depublier(self, request, pk=None):
        """
        Dépublie le formulaire.
        """
        formulaire = self.get_object()
        formulaire = depublier_formulaire(formulaire)
        serializer = self.get_serializer( formulaire)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Soumettre les réponses d'un formulaire",
        description=("Enregistre les réponses d'une candidature pour un formulaire. "
                    "Toutes les validations sont effectuées : cohérence candidature/campagne, "
                    "question appartient au formulaire, option appartient à la question, "
                    "questions obligatoires."),
        request=ReponseSubmissionSerializer,
        responses=ReponseCandidatureSerializer,
    )
    @action(detail=True, methods=["post"], url_path="soumettre-reponses",)
    def soumettre_reponses(self, request, pk=None):
        formulaire = self.get_object()
        serializer = ReponseSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        candidature = serializer.validated_data["candidature"]
        reponses_data = serializer.validated_data["reponses"]

        if candidature.campagne_id != formulaire.campagne_id:
            return Response(
                {"detail": "La candidature n'appartient pas à la campagne de ce formulaire."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        try:
            with transaction.atomic():
                result_reponses = []
                for reponse_data in reponses_data:
                    question = reponse_data["question"]

                    reponse_question, _ = ReponseQuestion.objects.get_or_create(
                        candidature=candidature,
                        question=question,
                        defaults={"valeur": ""},
                    )
                    reponse_question.options_selectionnees.all().delete()

                    if question.type_question in types_avec_options:
                        options = reponse_data.get("options", [])

                        if question.type_question == Question.TypeQuestion.CHECKBOX:
                            for option in options:
                                ReponseOption.objects.create(reponse=reponse_question, option=option)
                        else:
                            option = options[0]
                            reponse_question.valeur = option.valeur
                            reponse_question.save()
                            ReponseOption.objects.create(reponse=reponse_question, option=option)
                    else:
                        valeur = reponse_data.get("valeur", "")
                        reponse_question.valeur = valeur
                        reponse_question.save()

                    result_reponses.append(reponse_question)

            output_serializer = ReponseCandidatureSerializer({
                "candidature": candidature.id,
                "reponses": result_reponses,
            })
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


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
