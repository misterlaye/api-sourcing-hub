from datetime import date

from django.utils import timezone
import re
from rest_framework import serializers

from .models import (
    Referentiel,
    Campagne,
    CritereSelection,
    ReunionInformation,
    CreneauRI,
)

NUMERIC_ONLY_RE = re.compile(r'^\s*-?\d+([.,]\d+)?\s*$')


def validate_not_numeric_only(value, field_label):
    if NUMERIC_ONLY_RE.match(value):
        raise serializers.ValidationError(f"{field_label} ne peut pas être uniquement numérique.")
    return value


class ReferentielSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referentiel
        fields = ('id', 'title', 'description')

    def validate_title(self, value):
        return validate_not_numeric_only(value, "Le titre")


class CritereSelectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CritereSelection
        fields = ('id', 'name', 'description')

    def validate_name(self, value):
        return validate_not_numeric_only(value, "Le nom")


class CampagneSerializer(serializers.ModelSerializer):
    referentiel = ReferentielSerializer(read_only=True)

    criteres = CritereSelectionSerializer(
        many=True,
        read_only=True
    )

    referentiel_id = serializers.PrimaryKeyRelatedField(
        queryset=Referentiel.objects.all(),
        source='referentiel',
        write_only=True
    )

    criteres_ids = serializers.PrimaryKeyRelatedField(
        queryset=CritereSelection.objects.all(),
        source='criteres',
        write_only=True,
        many=True,
        required=False
    )

    reunion_information = serializers.SerializerMethodField()

    formulaire = serializers.SerializerMethodField()

    nombre_candidatures = serializers.IntegerField(
        source='candidatures.count',
        read_only=True
    )

    class Meta:
        model = Campagne
        fields = (
            'id',
            'title',
            'description',
            'created_at',
            'begin_date',
            'end_date',
            'status',
            'referentiel',
            'referentiel_id',
            'criteres',
            'criteres_ids',
            'reunion_information',
            'formulaire',
            'nombre_candidatures',
        )
        read_only_fields = ('created_at',)

    def get_reunion_information(self, obj):
        ri = getattr(obj, 'reunion_information', None)

        if not ri:
            return None

        return {
            'id': ri.id,
            'titre': ri.titre,
            'date': ri.date,
            'lieu': ri.lieu,
            'description': ri.description,
            'actif': ri.actif,
            'nombre_creneaux': ri.creneaux.count(),
        }

    def get_formulaire(self, obj):
        formulaire = getattr(obj, 'formulaire', None)

        if not formulaire:
            return None

        return {
            'id': formulaire.id,
            'titre': formulaire.titre,
            'publier': formulaire.publier,
            'actif': formulaire.actif,
        }

    def validate_title(self, value):
        return validate_not_numeric_only(
            value,
            "Le titre"
        )

    def validate(self, data):

        begin_date = data.get(
            'begin_date',
            getattr(self.instance, 'begin_date', None)
        )

        end_date = data.get(
            'end_date',
            getattr(self.instance, 'end_date', None)
        )

        today = timezone.now().date()
        is_creating = self.instance is None
        begin_date_changed = (
            self.instance is not None
            and 'begin_date' in data
            and data['begin_date'] != self.instance.begin_date
        )

        if (is_creating or begin_date_changed) and begin_date and begin_date < today:
            raise serializers.ValidationError({
                'begin_date':
                "La date de début ne peut pas être antérieure à aujourd'hui."
            })

        if (
            begin_date
            and end_date
            and end_date <= begin_date
        ):
            raise serializers.ValidationError({
                'end_date':
                "La date de fin doit être postérieure à la date de début."
            })

        return data


class CreneauRISerializer(serializers.ModelSerializer):
    nombre_candidats = serializers.SerializerMethodField()
    nombre_presents = serializers.SerializerMethodField()
    nombre_absents = serializers.SerializerMethodField()

    class Meta:
        model = CreneauRI
        fields = [
            'id',
            'reunion',
            'nom',
            'heure_debut',
            'heure_fin',
            'capacite',
            'nombre_candidats',
            'nombre_presents',
            'nombre_absents',
        ]
        read_only_fields = ['id', 'nombre_candidats', 'nombre_presents', 'nombre_absents']
        extra_kwargs = {
            'reunion': {'required': False},
            'nom': {'required': False, 'allow_blank': True},
        }

    def get_nombre_candidats(self, obj):
        return obj.convocations.count()

    def get_nombre_presents(self, obj):
        return obj.convocations.filter(statut="present").count()

    def get_nombre_absents(self, obj):
        return obj.convocations.filter(statut="absent").count()

    def validate(self, attrs):
        heure_debut = attrs.get('heure_debut', getattr(self.instance, 'heure_debut', None))
        heure_fin = attrs.get('heure_fin', getattr(self.instance, 'heure_fin', None))
        capacite = attrs.get('capacite', getattr(self.instance, 'capacite', None))

        if heure_debut is not None and heure_fin is not None and heure_fin <= heure_debut:
            raise serializers.ValidationError(
                {"heure_fin": "L'heure de fin doit être supérieure à l'heure de début."}
            )

        if capacite is not None and capacite <= 0:
            raise serializers.ValidationError(
                {"capacite": "La capacité doit être supérieure à 0."}
            )

        reunion = self.context.get('reunion', attrs.get('reunion', getattr(self.instance, 'reunion', None)))
        if reunion:
            queryset = CreneauRI.objects.filter(reunion=reunion)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            for creneau in queryset:
                if (heure_debut < creneau.heure_fin and heure_fin > creneau.heure_debut):
                    raise serializers.ValidationError(
                        "Ce créneau chevauche un créneau existant."
                    )

        return attrs


class ReunionInformationSerializer(serializers.ModelSerializer):
    creneaux = CreneauRISerializer(many=True, read_only=True)
    total_convoques = serializers.SerializerMethodField()
    total_presents = serializers.SerializerMethodField()
    total_absents = serializers.SerializerMethodField()

    class Meta:
        model = ReunionInformation
        fields = [
            'id',
            'campagne',
            'titre',
            'date',
            'lieu',
            'description',
            'actif',
            'date_creation',
            'date_modification',
            'creneaux',
            'total_convoques',
            'total_presents',
            'total_absents',
        ]
        read_only_fields = ['campagne', 'total_convoques', 'total_presents', 'total_absents']

    def get_total_convoques(self, obj):
        return obj.convocations.count()

    def get_total_presents(self, obj):
        return obj.convocations.filter(statut="present").count()

    def get_total_absents(self, obj):
        return obj.convocations.filter(statut="absent").count()

