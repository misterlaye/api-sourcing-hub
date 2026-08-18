from rest_framework import serializers
from .models import Candidature


class CandidatureCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidature
        fields = ["id", "campagne", "nom", "prenom", "email", "telephone"]


class CandidatureSerializer(serializers.ModelSerializer):
    campagne_titre = serializers.CharField(source="campagne.title", read_only=True)

    class Meta:
        model = Candidature
        fields = [
            "id", "campagne", "campagne_titre",
            "nom", "prenom", "email", "telephone",
            "status", "date_soumission",
        ]
        read_only_fields = ["date_soumission"]