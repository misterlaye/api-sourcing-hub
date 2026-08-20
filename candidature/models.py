import uuid
from django.db import models
from campagne.models import Campagne


class Candidature(models.Model):
    """
    Une candidature = un candidat qui postule à une campagne.
    Chaque candidat possède un QR token unique généré automatiquement,
    qui sert d'identifiant sécurisé pour la Réunion d'Information (RI).
    """

    class Status(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        PRESENT = "present", "Présent"
        ABSENT = "absent", "Absent"

    campagne = models.ForeignKey(
        Campagne,
        on_delete=models.CASCADE,
        related_name="candidatures",
    )

    nom = models.CharField(max_length=255)
    prenom = models.CharField(max_length=255)
    email = models.EmailField()
    telephone = models.CharField(max_length=20, blank=True)

    # QR token unique par candidat (1 candidat = 1 QR code unique immuable)
    qr_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        help_text="Token unique sécurisé associé au candidat pour son QR code."
    )

    # Statut par défaut = EN_ATTENTE lors de la soumission du formulaire public
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.EN_ATTENTE,
    )

    date_soumission = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_soumission"]

    def __str__(self):
        return f"{self.prenom} {self.nom} - {self.campagne.title}"


class Convocation(models.Model):
    """
    Convocation d'un candidat à une étape du processus (RI ou Entretiens).
    Pour la Réunion d'Information (RI) :
    - Un PDF avec le QR code unique est généré et envoyé par email au candidat.
    - L'administrateur scanne ce QR code avec sa webcam lors de la RI pour marquer la présence.
    Pour les entretiens suivants (Technique, Motivation, Final) :
    - Le candidat possède déjà son compte et consulte ses convocations en ligne (sans QR code).
    """

    class Type(models.TextChoices):
        RI = "RI", "Réunion d'Information"
        TECHNIQUE = "TECHNIQUE", "Entretien technique"
        MOTIVATION = "MOTIVATION", "Entretien motivation"
        FINAL = "FINAL", "Entretien final"

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        PRESENT = "present", "Présent"
        ABSENT = "absent", "Absent"
        ANNULEE = "annulee", "Annulée"

    candidature = models.ForeignKey(
        Candidature,
        on_delete=models.CASCADE,
        related_name="convocations",
    )
    campagne = models.ForeignKey(
        Campagne,
        on_delete=models.CASCADE,
        related_name="convocations",
    )
    type = models.CharField(
        max_length=50,
        choices=Type.choices,
        default=Type.RI,
    )
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField(null=True, blank=True)
    lieu = models.CharField(max_length=255, default="Simplon Sénégal")

    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
    )
    presence_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date et heure exactes auxquelles la présence a été validée via le scan QR."
    )

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "heure_debut"]

    def __str__(self):
        return f"Convocation {self.get_type_display()} - {self.candidature.prenom} {self.candidature.nom} ({self.date})"

    @property
    def qr_token(self):
        """Le QR code de la convocation utilise le token unique du candidat."""
        return self.candidature.qr_token


class ConvocationRI(models.Model):
    """
    Convocation spécifique d'un candidat à la Réunion d'Information (RI) d'une campagne.
    - Le candidat n'a pas besoin de compte pour recevoir son QR code ou assister à la RI.
    - Un token unique immuable sert pour le QR Code.
    - L'admin scanne le QR code lors de la RI pour marquer la présence (ABSENT -> PRESENT).
    - Une seule convocation RI par candidature et par RI (contrainte d'unicité).
    """

    class StatutPresence(models.TextChoices):
        ABSENT = "absent", "Absent"
        PRESENT = "present", "Présent"

    candidature = models.ForeignKey(
        Candidature,
        on_delete=models.CASCADE,
        related_name="convocations_ri",
    )
    reunion_information = models.ForeignKey(
        "campagne.ReunionInformation",
        on_delete=models.CASCADE,
        related_name="convocations",
    )
    creneau = models.ForeignKey(
        "campagne.CreneauRI",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="convocations",
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        help_text="Token unique sécurisé associé au QR code de la convocation RI.",
    )
    statut = models.CharField(
        max_length=20,
        choices=StatutPresence.choices,
        default=StatutPresence.ABSENT,
    )
    date_envoi = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date et heure de l'envoi de l'email de convocation.",
    )
    date_presence = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date et heure exactes auxquelles la présence a été validée via le scan QR.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["candidature", "reunion_information"],
                name="unique_candidature_reunion_ri",
            )
        ]

    def __str__(self):
        return f"Convocation RI - {self.candidature.prenom} {self.candidature.nom} ({self.reunion_information})"