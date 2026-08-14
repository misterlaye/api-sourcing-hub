from django.utils import timezone
import re
from rest_framework import serializers
from .models import Referentiel, Campagne, CritereSelection

# Chaîne composée uniquement de chiffres (avec éventuellement espaces, signe, décimale)
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
    criteres = CritereSelectionSerializer(many=True, read_only=True)


    referentiel_id = serializers.PrimaryKeyRelatedField(
        queryset=Referentiel.objects.all(), source='referentiel', write_only=True
    )
    criteres_ids = serializers.PrimaryKeyRelatedField(
        queryset=CritereSelection.objects.all(), source='criteres',
        write_only=True, many=True
    )


    class Meta:
        model = Campagne
        fields = (
            'id', 'title', 'description', 'created_at',
            'begin_date', 'end_date', 'status',
            'referentiel', 'referentiel_id',
            'criteres','criteres_ids'
        )
        read_only_fields = ('created_at',)

    def validate_title(self, value):
        return validate_not_numeric_only(value, "Le titre")

    def validate(self, data):
        begin_date = data.get('begin_date', getattr(self.instance, 'begin_date', None))
        end_date = data.get('end_date', getattr(self.instance, 'end_date', None))
        Created_at = data.get('created_at', getattr(self.instance, 'created_at', None))

        if begin_date and begin_date < timezone.now().date():
            raise serializers.ValidationError(
                {"begin_date": "La date de début ne peut pas être antérieure à aujourd'hui."}
            )
    
        if begin_date and end_date and end_date <= begin_date:
            raise serializers.ValidationError(
                {"end_date": "La date de fin doit être postérieure à la date de début."}
            )

        return data