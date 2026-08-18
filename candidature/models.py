from django.db import models
from campagne.models import Campagne


class Candidature(models.Model):
    """
    Une candidature = un candidat qui postule à une campagne.
    """

    class Status(models.TextChoices):
        ABSENT = "absent", "Absent"
        PRESENT = "present", "Présent"

    campagne = models.ForeignKey(
        Campagne,
        on_delete=models.CASCADE,
        related_name="candidatures",
    )

    nom = models.CharField(max_length=255)
    prenom = models.CharField(max_length=255)
    email = models.EmailField()
    telephone = models.CharField(max_length=20, blank=True)

    # Statut par défaut = ABSENT, tant que le jury n'a pas
    # confirmé la présence du candidat à l'entretien
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ABSENT,
    )

    date_soumission = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_soumission"]

    def __str__(self):
        return f"{self.prenom} {self.nom} - {self.campagne.title}"