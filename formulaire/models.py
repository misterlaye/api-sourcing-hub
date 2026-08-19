from django.db import models

class Formulaire(models.Model):
     # Une campagne possède un seul formulaire.
    # On utilise OneToOneField car ton besoin est :
    # Campagne 1 -------- 1 Formulaire
    campagne= models.OneToOneField("campagne.Campagne", on_delete=models.CASCADE,related_name="formulaire",)
    titre=models.TextField(blank=True)
    description=models.TextField(blank=True)
    # indiquer si e formulaire est publie
    publier=models.BooleanField(default=False)
     # Permet d'activer ou désactiver le formulaire.
    actif = models.BooleanField(default=True)
    date_creation= models.DateTimeField(auto_now=True)
    date_modification=models.DateTimeField(auto_now=True)

    class Meta:
        ordering=["date_creation"]

    
    def __str__(self):
        return self.titre


class SectionFormulaire(models.Model):
    # Une section appartient à un formulaire

    formulaire=models.ForeignKey(Formulaire,on_delete=models.CASCADE,related_name="sections",)
    titre=models.CharField(max_length=200)
    description=models.TextField(blank=True)
    # Permet de determiner l ordre des sections
    ordre=models.PositiveIntegerField(default=0)



    class Meta:
        ordering = ["ordre", "id"]

    def __str__(self):
        return self.titre


class Question(models.Model):
    """
    Question dynamique du formulaire.

    L'administrateur peut créer autant de questions
    qu'il souhaite.
    """
    class TypeQuestion(models.TextChoices):
        TEXT = "TEXT", "Texte"

        TEXTAREA = "TEXTAREA", "Texte long"

        RADIO = "RADIO", "Choix unique"

        CHECKBOX = "CHECKBOX", "Choix multiples"

        SELECT = "SELECT", "Liste déroulante"

        NUMBER = "NUMBER", "Nombre"

        EMAIL = "EMAIL", "Email"

        DATE = "DATE", "Date"

        YES_NO = "YES_NO", "Oui / Non"

        # La question appartient à une section.
    section=models.ForeignKey(SectionFormulaire,on_delete=models.CASCADE,related_name="questions",)
    texte = models.TextField()
    type_question = models.CharField(max_length=20,choices=TypeQuestion.choices,)
    # Indique si la réponse est obligatoire.
    obligatoire = models.BooleanField(default=False )
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordre", "id"]

    def __str__(self):
        return self.texte
class OptionQuestion(models.Model):
    """
    Option d'une question.

    Utilisée principalement pour :
    - RADIO
    - CHECKBOX
    - SELECT
    """

    # Une option appartient à une question.
    question = models.ForeignKey( Question, on_delete=models.CASCADE,related_name="options",)
    texte = models.CharField( max_length=255)
    # Valeur envoyée au backend.
    valeur = models.CharField( max_length=255)
    ordre = models.PositiveIntegerField(default=0 )

    class Meta:
        ordering = ["ordre", "id"]

    def __str__(self):
        return self.texte


class ReponseQuestion(models.Model):
    """
    Réponse d'une candidature à une question.
    """

    candidature = models.ForeignKey(
        "candidature.Candidature",
        on_delete=models.CASCADE,
        related_name="reponses",
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="reponses",
    )

    valeur = models.TextField(blank=True)

    date_reponse = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["candidature", "question"],
                name="unique_candidature_question",
            )
        ]
        ordering = ["question__ordre", "question__id"]

    def __str__(self):
        return f"Réponse de {self.candidature} à {self.question}"


class ReponseOption(models.Model):
    """
    Option sélectionnée par une candidature pour une réponse.
    """

    reponse = models.ForeignKey(
        ReponseQuestion,
        on_delete=models.CASCADE,
        related_name="options_selectionnees",
    )

    option = models.ForeignKey(
        OptionQuestion,
        on_delete=models.CASCADE,
        related_name="reponses",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reponse", "option"],
                name="unique_reponse_option",
            )
        ]
        ordering = ["option__ordre", "option__id"]

    def __str__(self):
        return f"Option {self.option} pour réponse {self.reponse}"