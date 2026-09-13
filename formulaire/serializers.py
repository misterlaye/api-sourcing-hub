from rest_framework import serializers

from .models import Formulaire , SectionFormulaire ,Question, OptionQuestion


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