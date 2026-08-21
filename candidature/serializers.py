from rest_framework import serializers
from .models import Candidature, Convocation, ConvocationRI
from .services import send_convocation_email
from campagne.models import CreneauRI, ReunionInformation


class CandidatureCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidature
        fields = ["id", "campagne", "nom", "prenom", "email", "telephone"]


class CandidatureSerializer(serializers.ModelSerializer):
    campagne_titre = serializers.CharField(source="campagne.title", read_only=True)
    qr_token = serializers.UUIDField(read_only=True)

    class Meta:
        model = Candidature
        fields = [
            "id",
            "campagne",
            "campagne_titre",
            "nom",
            "prenom",
            "email",
            "telephone",
            "qr_token",
            "status",
            "date_soumission",
        ]
        read_only_fields = ["qr_token", "date_soumission"]


class ConvocationRISerializer(serializers.ModelSerializer):
    candidature_nom = serializers.CharField(source="candidature.nom", read_only=True)
    candidature_prenom = serializers.CharField(source="candidature.prenom", read_only=True)
    candidature_email = serializers.CharField(source="candidature.email", read_only=True)
    candidature_telephone = serializers.CharField(source="candidature.telephone", read_only=True)
    reunion_titre = serializers.CharField(source="reunion_information.titre", read_only=True)
    reunion_date = serializers.DateField(source="reunion_information.date", read_only=True)
    reunion_lieu = serializers.CharField(source="reunion_information.lieu", read_only=True)
    creneau_nom = serializers.CharField(source="creneau.nom", read_only=True, default="")
    creneau_heure_debut = serializers.TimeField(source="creneau.heure_debut", read_only=True)
    creneau_heure_fin = serializers.TimeField(source="creneau.heure_fin", read_only=True)

    class Meta:
        model = ConvocationRI
        fields = [
            "id",
            "candidature",
            "candidature_nom",
            "candidature_prenom",
            "candidature_email",
            "candidature_telephone",
            "reunion_information",
            "reunion_titre",
            "reunion_date",
            "reunion_lieu",
            "creneau",
            "creneau_nom",
            "creneau_heure_debut",
            "creneau_heure_fin",
            "token",
            "statut",
            "date_envoi",
            "date_presence",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "token",
            "statut",
            "date_envoi",
            "date_presence",
            "created_at",
            "updated_at",
        ]


class ConvocationRICreateBatchSerializer(serializers.Serializer):
    candidature_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        help_text="Liste des IDs de candidatures à convoquer."
    )
    creneau_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID du créneau (ex: Groupe matin ou soir)."
    )
    envoyer_email = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Envoyer immédiatement le PDF avec QR code par email."
    )


class CampagneCandidatSerializer(serializers.ModelSerializer):
    campagne_id = serializers.IntegerField(source="campagne.id", read_only=True)
    campagne_titre = serializers.CharField(source="campagne.title", read_only=True)
    convocation_ri = serializers.SerializerMethodField()

    class Meta:
        model = Candidature
        fields = [
            "id",
            "campagne",
            "campagne_id",
            "campagne_titre",
            "nom",
            "prenom",
            "email",
            "telephone",
            "qr_token",
            "status",
            "date_soumission",
            "convocation_ri",
        ]

    def get_convocation_ri(self, obj):
        # Récupérer la convocation RI associée à cette candidature si elle existe
        convocation = obj.convocations_ri.first()
        if not convocation:
            return None
        return {
            "id": convocation.id,
            "token": str(convocation.token),
            "statut": convocation.statut,
            "creneau_id": convocation.creneau_id,
            "creneau_nom": convocation.creneau.nom if convocation.creneau else None,
            "creneau_heure_debut": str(convocation.creneau.heure_debut)[:5] if convocation.creneau else None,
            "creneau_heure_fin": str(convocation.creneau.heure_fin)[:5] if convocation.creneau and convocation.creneau.heure_fin else None,
            "date_envoi": convocation.date_envoi.isoformat() if convocation.date_envoi else None,
            "date_presence": convocation.date_presence.isoformat() if convocation.date_presence else None,
        }


class ConvocationSerializer(serializers.ModelSerializer):
    candidature_nom = serializers.CharField(source="candidature.nom", read_only=True)
    candidature_prenom = serializers.CharField(source="candidature.prenom", read_only=True)
    candidature_email = serializers.CharField(source="candidature.email", read_only=True)
    campagne_titre = serializers.CharField(source="campagne.title", read_only=True)
    qr_token = serializers.CharField(read_only=True)

    class Meta:
        model = Convocation
        fields = [
            "id",
            "candidature",
            "candidature_nom",
            "candidature_prenom",
            "candidature_email",
            "campagne",
            "campagne_titre",
            "type",
            "date",
            "heure_debut",
            "heure_fin",
            "lieu",
            "statut",
            "presence_at",
            "qr_token",
            "date_creation",
        ]
        read_only_fields = ["presence_at", "qr_token", "date_creation"]


class ConvocationCreateSerializer(serializers.ModelSerializer):
    envoyer_email = serializers.BooleanField(default=True, write_only=True, required=False)

    class Meta:
        model = Convocation
        fields = [
            "id",
            "candidature",
            "campagne",
            "type",
            "date",
            "heure_debut",
            "heure_fin",
            "lieu",
            "envoyer_email",
        ]

    def create(self, validated_data):
        envoyer_email = validated_data.pop("envoyer_email", True)
        convocation = super().create(validated_data)
        if envoyer_email and convocation.type == Convocation.Type.RI:
            send_convocation_email(convocation)
        return convocation


class ScanQRSerializer(serializers.Serializer):
    token = serializers.CharField(required=False, allow_blank=True)
    qr_token = serializers.CharField(required=False, allow_blank=True)
    campagne = serializers.IntegerField(required=False, allow_null=True)
    reunion = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        token_val = attrs.get("token") or attrs.get("qr_token")
        if not token_val:
            raise serializers.ValidationError("Le token QR code est obligatoire.")
        attrs["token"] = token_val.strip()
        return attrs