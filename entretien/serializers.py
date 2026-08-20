from rest_framework import serializers
from accounts.models import User
from campagne.models import Campagne
from candidature.models import Candidature
from .models import Entretien, CreneauEntretien, ConvocationEntretien


class JurySummarySerializer(serializers.ModelSerializer):
    """Représentation simplifiée d'un membre du jury."""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name", "role"]

    def get_full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else obj.email


class CandidatSummarySerializer(serializers.ModelSerializer):
    """Représentation simplifiée d'un candidat pour les créneaux et convocations."""
    class Meta:
        model = Candidature
        fields = ["id", "nom", "prenom", "email", "telephone", "status"]


class CreneauEntretienSerializer(serializers.ModelSerializer):
    """Serializer pour la gestion des créneaux d'entretiens."""
    candidature_details = CandidatSummarySerializer(source="candidature", read_only=True)
    jurys_details = JurySummarySerializer(source="jurys", many=True, read_only=True)
    jury_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        source="jurys",
        required=False,
        write_only=True
    )

    class Meta:
        model = CreneauEntretien
        fields = [
            "id",
            "entretien",
            "candidature",
            "candidature_details",
            "date",
            "heure_debut",
            "heure_fin",
            "jury_ids",
            "jurys_details",
            "statut",
        ]
        read_only_fields = ["id"]


class ConvocationEntretienSerializer(serializers.ModelSerializer):
    """Serializer pour la consultation des convocations officielles aux entretiens."""
    candidature_details = CandidatSummarySerializer(source="candidature", read_only=True)
    campagne_titre = serializers.CharField(source="entretien.campagne.title", read_only=True)
    type_display = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = ConvocationEntretien
        fields = [
            "id",
            "entretien",
            "campagne_titre",
            "candidature",
            "candidature_details",
            "creneau",
            "type",
            "type_display",
            "date",
            "heure_debut",
            "heure_fin",
            "lieu",
            "lien_visio",
            "statut",
            "date_envoi",
            "date_creation",
        ]
        read_only_fields = ["id", "date_creation", "date_envoi"]


class CreneauInputSerializer(serializers.Serializer):
    """Serializer pour la saisie imbriquée d'un créneau lors de la création d'un entretien."""
    candidature_id = serializers.IntegerField()
    heure_debut = serializers.TimeField()
    heure_fin = serializers.TimeField()
    date = serializers.DateField(required=False, allow_null=True)
    jury_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )


class EntretienSerializer(serializers.ModelSerializer):
    """Serializer principal pour la création et la gestion des sessions d'entretiens."""
    campagne_titre = serializers.CharField(source="campagne.title", read_only=True)
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    jurys_details = JurySummarySerializer(source="jurys", many=True, read_only=True)
    jury_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        source="jurys",
        required=False,
        write_only=True
    )
    creneaux = CreneauEntretienSerializer(many=True, read_only=True)
    creneaux_input = CreneauInputSerializer(many=True, required=False, write_only=True)
    total_candidats = serializers.SerializerMethodField()
    total_jurys = serializers.SerializerMethodField()

    class Meta:
        model = Entretien
        fields = [
            "id",
            "campagne",
            "campagne_titre",
            "type",
            "type_display",
            "statut",
            "date",
            "heure_debut",
            "heure_fin",
            "duree_minutes",
            "lieu",
            "lien_visio",
            "notes",
            "jury_ids",
            "jurys_details",
            "creneaux",
            "creneaux_input",
            "total_candidats",
            "total_jurys",
            "date_creation",
            "date_modification",
        ]
        read_only_fields = ["id", "date_creation", "date_modification", "statut"]

    def get_total_candidats(self, obj):
        return obj.creneaux.filter(candidature__isnull=False).count()

    def get_total_jurys(self, obj):
        return obj.jurys.count()

    def create(self, validated_data):
        creneaux_data = validated_data.pop("creneaux_input", [])
        jurys = validated_data.pop("jurys", [])
        
        entretien = Entretien.objects.create(**validated_data)
        if jurys:
            entretien.jurys.set(jurys)

        for c_data in creneaux_data:
            candidature = Candidature.objects.get(id=c_data["candidature_id"])
            creneau = CreneauEntretien.objects.create(
                entretien=entretien,
                candidature=candidature,
                date=c_data.get("date") or entretien.date,
                heure_debut=c_data["heure_debut"],
                heure_fin=c_data["heure_fin"],
            )
            jury_ids = c_data.get("jury_ids", [])
            if jury_ids:
                creneau.jurys.set(User.objects.filter(id__in=jury_ids))

        return entretien


class ConfirmationEntretienSerializer(serializers.Serializer):
    """Paramètres pour l'action de confirmation et envoi des convocations."""
    envoyer_emails = serializers.BooleanField(
        default=True,
        help_text="Déclenche l'envoi des emails aux candidats et aux jurys si True."
    )
