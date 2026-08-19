from rest_framework import serializers

from candidature.models import Candidature
from .models import Formulaire , SectionFormulaire ,Question, OptionQuestion, ReponseQuestion, ReponseOption


class ReponseOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model= ReponseOption
        fields=["id","reponse","option",]
        read_only_fields = ["id",]


class ReponseQuestionSerializer(serializers.ModelSerializer):
    options_selectionnees=ReponseOptionSerializer(many=True,read_only=True,)
    class Meta:
        model=ReponseQuestion
        fields = ["id","candidature","question","valeur","date_reponse","options_selectionnees",]
        read_only_fields = ["id","date_reponse",]


class ReponseQuestionCreateSerializer(serializers.Serializer):
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    valeur = serializers.CharField(required=False, allow_blank=True)
    options = serializers.PrimaryKeyRelatedField(queryset=OptionQuestion.objects.all(), many=True, required=False)


class ReponseSubmissionSerializer(serializers.Serializer):
    reponses = ReponseQuestionCreateSerializer(many=True)


class ReponseOptionDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='option.id')
    texte = serializers.CharField(source='option.texte')
    valeur = serializers.CharField(source='option.valeur')


class ReponseQuestionDetailSerializer(serializers.ModelSerializer):
    question = serializers.IntegerField(source='question.id')
    question_texte = serializers.CharField(source='question.texte')
    type_question = serializers.CharField(source='question.type_question')
    valeur = serializers.CharField()
    options = ReponseOptionDetailSerializer(source='options_selectionnees', many=True)

    class Meta:
        model = ReponseQuestion
        fields = ["question", "question_texte", "type_question", "valeur", "options"]


class ReponseCandidatureSerializer(serializers.Serializer):
    candidature = serializers.IntegerField()
    reponses = ReponseQuestionDetailSerializer(many=True)


class OptionQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model= OptionQuestion
        fields=["id","question","texte","valeur","ordre",]
        read_only_fields = ["id",]
class QuestionSerializer(serializers.ModelSerializer):
    """
    Serializer d'une question.

    Les options sont incluses directement dans la réponse.
    Cela permet au frontend Vue.js d'afficher facilement
    les choix d'une question.
    """
    options=OptionQuestionSerializer(many=True,read_only=True,)
    class Meta:
        model=Question
        fields = ["id","section","texte","type_question","obligatoire","ordre","options",]
        read_only_fields = ["id",]
    def validate(self, attrs):
        texte=attrs.get("texte")
        # Une question doit obligatoirement avoir un texte.
        if texte is not None and not texte.strip():
            raise serializers.ValidationError({"le texte de la question est obligatoire"})
        return attrs

class SectionFormulaireSerializer(serializers.ModelSerializer):

    #Serializer d'une section du formulaire.

   # Les questions de la section sont retournées
   # directement dans la réponse JSON.
     
    questions=QuestionSerializer(many=True,read_only=True,)
    class Meta:
        model = SectionFormulaire

        fields = ["id","formulaire", "titre","ordre","questions",]
        read_only_fields = ["id",]

    def validate(self, attrs):
        """
        Vérifie les informations de la section.
        """
        titre = attrs.get("titre")
        if titre is not None and not titre.strip():
            raise serializers.ValidationError(
                {
                    "titre": "Le titre de la section est obligatoire."
                }
            )

        return attrs


class FormulaireSerializer(serializers.ModelSerializer):
  
    sections = SectionFormulaireSerializer(many=True,read_only=True,)

    class Meta:
        model = Formulaire
        fields = [
            "id",
            "campagne",
            "titre",
            "description",
            "publier",
            "actif",
            "sections",
            "date_creation",
            "date_modification",
        ]

        read_only_fields = [
            "id",
            "date_creation",
            "date_modification",
        ]

    def validate(self, attrs):
        """
        Vérifie les informations du formulaire.
        """
        titre = attrs.get("titre")
        if titre is not None and not titre.strip():
            raise serializers.ValidationError(
                {
                    "titre": "Le titre du formulaire est obligatoire."
                }
            )

        return attrs


class FormulairePreviewSerializer(serializers.ModelSerializer):
   
    sections = SectionFormulaireSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Formulaire

        fields = [
            "id",
            "titre",
            "description",
            "sections",
        ]
