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
    nom = serializers.CharField(required=False, allow_blank=True, default="")
    prenom = serializers.CharField(required=False, allow_blank=True, default="")
    email = serializers.CharField(required=False, allow_blank=True, default="")
    telephone = serializers.CharField(required=False, allow_blank=True, default="")
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


class MesReponsesSerializer(serializers.Serializer):
    reponses = ReponseQuestionDetailSerializer(many=True)


class ReponseCandidatureSerializer(serializers.Serializer):
    candidature = serializers.IntegerField()
    reponses = ReponseQuestionDetailSerializer(many=True)


class OptionQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model= OptionQuestion
        fields=["id","question","texte","valeur","ordre",]
        read_only_fields = ["id",]

class OptionQuestionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptionQuestion
        fields = ["id", "texte", "valeur", "ordre"]
        read_only_fields = ["id"]

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
            raise serializers.ValidationError({"texte": "Le texte de la question est obligatoire."})
        return attrs

class QuestionWriteSerializer(serializers.ModelSerializer):
    options = OptionQuestionWriteSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ["id", "texte", "type_question", "obligatoire", "ordre", "options"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        question = Question.objects.create(**validated_data)
        for option_data in options_data:
            OptionQuestion.objects.create(question=question, **option_data)
        return question

    def update(self, instance, validated_data):
        options_data = validated_data.pop('options', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if options_data is not None:
            ReponseOption.objects.filter(option__question=instance).delete()
            instance.options.all().delete()
            for option_data in options_data:
                OptionQuestion.objects.create(question=instance, **option_data)
        return instance

class SectionFormulaireSerializer(serializers.ModelSerializer):

    #Serializer d'une section du formulaire.

   # Les questions de la section sont retournées
   # directement dans la réponse JSON.
      
    questions=QuestionSerializer(many=True,read_only=True,)
    class Meta:
        model = SectionFormulaire

        fields = ["id","formulaire", "titre","description","ordre","questions",]
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

class SectionFormulaireWriteSerializer(serializers.ModelSerializer):
    questions = QuestionWriteSerializer(many=True, required=False)

    class Meta:
        model = SectionFormulaire
        fields = ["id", "titre", "description", "ordre", "questions"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        section = SectionFormulaire.objects.create(**validated_data)
        for question_data in questions_data:
            options_data = question_data.pop('options', [])
            question = Question.objects.create(section=section, **question_data)
            for option_data in options_data:
                OptionQuestion.objects.create(question=question, **option_data)
        return section

    def update(self, instance, validated_data):
        questions_data = validated_data.pop('questions', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if questions_data is not None:
            ReponseQuestion.objects.filter(question__section=instance).delete()
            for question in instance.questions.all():
                question.delete()
            for question_data in questions_data:
                options_data = question_data.pop('options', [])
                question = Question.objects.create(section=instance, **question_data)
                for option_data in options_data:
                    OptionQuestion.objects.create(question=question, **option_data)
        return instance


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


class FormulaireWriteSerializer(serializers.ModelSerializer):
    sections = SectionFormulaireWriteSerializer(many=True, required=False)

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
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        sections_data = validated_data.pop('sections', [])
        formulaire = Formulaire.objects.create(**validated_data)
        for section_data in sections_data:
            questions_data = section_data.pop('questions', [])
            section = SectionFormulaire.objects.create(formulaire=formulaire, **section_data)
            for question_data in questions_data:
                options_data = question_data.pop('options', [])
                question = Question.objects.create(section=section, **question_data)
                for option_data in options_data:
                    OptionQuestion.objects.create(question=question, **option_data)
        return formulaire

    def update(self, instance, validated_data):
        sections_data = validated_data.pop('sections', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if sections_data is not None:
            for section in instance.sections.all():
                section.delete()
            for section_data in sections_data:
                questions_data = section_data.pop('questions', [])
                section = SectionFormulaire.objects.create(formulaire=instance, **section_data)
                for question_data in questions_data:
                    options_data = question_data.pop('options', [])
                    question = Question.objects.create(section=section, **question_data)
                    for option_data in options_data:
                        OptionQuestion.objects.create(question=question, **option_data)
        return instance


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
