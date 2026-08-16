from django.shortcuts import render

# Create your views here.
from rest_framework import status , viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .models import Formulaire, SectionFormulaire, Question, OptionQuestion
from .serializers import FormulaireSerializer, FormulairePreviewSerializer, SectionFormulaireSerializer, QuestionSerializer, OptionQuestionSerializer
from .permissions import IsAdministrateur
from .services import publier_formulaire,depublier_formulaire


class FormulaireViewSet(viewsets.ModelViewSet):
    # Api permet de gere les formulaire et le formulaire est lie a une campagne
    serializer_class= FormulaireSerializer
    def get_queryset(self):
        #recupere les formlaires avec leus sections , options etc
        # Cela évite de multiplier inutilement les requêtes
        #SQL lorsque Vue.js demande un formulaire complet. 
        return Formulaire.objects.select_related("campagne").prefetch_related(Prefetch("sections",queryset=(SectionFormulaire.objects.order_by("ordre","id").prefetch_related(Pretech("questions",queryset=(Question.objects.order_by("odre","id").prefetch_related("options")
        ),)),
        )))
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
                IsAuthenticated(),
            ]
        # Les opérations de lecture nécessitent
        # seulement une authentification.
        return [
            IsAuthenticated(),
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
        Responses= FormulairePreviewSerializer,

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
        Response=FormulaireSerializer,
    )

    @action(detail=True,methods=["post"],url_path="publier",)
    def publier(self,request,pk=None):
        Formulaire= self.get_object()
        try:
            formulaire=publier_formulaire(formulaire)
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
class SectionFormulaireViewSet(viewsets.ModelViewSet):
    # API pour la gestion des sections
    serializer_class= SectionFormulaireSerializer
    def get_queryset(self):
        """
        Permet de récupérer les sections d'un formulaire.

        Exemple :

        /api/sections/?formulaire=1
        """
        queryset = (SectionFormulaire.objectsprefetch_related( "questions__options" )
        )
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
                IsAuthenticated(),
                IsAdministrateur(),
            ]

        return [
            IsAuthenticated(),
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
                IsAuthenticated(),
                IsAdministrateur(),
            ]

        return [
            IsAuthenticated(),
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
                IsAuthenticated(),
                IsAdministrateur(),
            ]

        return [
            IsAuthenticated(),
        ]