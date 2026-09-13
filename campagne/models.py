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
    criteres = models.ManyToManyField(CritereSelection, related_name='campagnes', null=True)


    def __str__(self):
            return self.title


class ReunionInformation(models.Model):
    ri_date = models.DateField()
    begin_hour = models.TimeField()
    end_hour = models.TimeField()
    location = models.CharField(max_length=255) 
    campagne = models.ForeignKey(Campagne, on_delete=models.CASCADE, related_name='ri')
 