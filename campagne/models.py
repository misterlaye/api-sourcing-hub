from django.db import models

class Referentiel(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
            return self.title

class CritereSelection(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()


    def __str__(self):
        return self.name

    
class Campagne(models.Model):
    class Status (models.TextChoices):
        BROUILLON = 'brouillon', 'Brouillon'
        PUBLIEE = 'publiee', 'Publiée'
        CLOTUREE = 'cloturee', 'Cloturée'


    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateField(auto_now_add=True)
    begin_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default= Status.BROUILLON

    )
    referentiel = models.ForeignKey(Referentiel, on_delete=models.PROTECT, related_name='campagnes')
    criteres = models.ManyToManyField(CritereSelection, related_name='campagnes', blank=True)


    def __str__(self):
            return self.title


class ReunionInformation(models.Model):
    campagne = models.OneToOneField(
        "campagne.Campagne",
        on_delete=models.CASCADE,
        related_name="reunion_information"
    )
    titre = models.CharField(max_length=255)
    date = models.DateField()
    lieu = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.titre} - {self.campagne}"


class CreneauRI(models.Model):
    reunion = models.ForeignKey(
        ReunionInformation,
        on_delete=models.CASCADE,
        related_name="creneaux"
    )
    nom = models.CharField(max_length=100, blank=True, default="", help_text="Nom du créneau ou du groupe (ex: Groupe matin, Groupe soir)")
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    capacite = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["heure_debut"]

    def __str__(self):
        if self.nom:
            return f"{self.nom} ({self.heure_debut} - {self.heure_fin})"
        return f"{self.heure_debut} - {self.heure_fin}"
