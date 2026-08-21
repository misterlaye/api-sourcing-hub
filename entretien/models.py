from django.conf import settings
from django.db import models
from django.db.models import Sum


class Entretien(models.Model):
    """
    Session d'évaluation / entretiens pour une campagne de recrutement donnée.
    Peut comporter plusieurs créneaux horaires et regrouper un ou plusieurs jurys
    et des candidats convoqués.
    """

    class Type(models.TextChoices):
        TECHNIQUE = "TECHNIQUE", "Entretien technique"
        MOTIVATION = "MOTIVATION", "Entretien motivation"
        FINAL = "FINAL", "Entretien final"

    class Statut(models.TextChoices):
        BROUILLON = "BROUILLON", "Brouillon"
        PLANIFIE = "PLANIFIE", "Planifié"
        CONFIRME = "CONFIRME", "Confirmé"
        TERMINE = "TERMINE", "Terminé"
        ANNULE = "ANNULE", "Annulé"

    campagne = models.ForeignKey(
        "campagne.Campagne",
        on_delete=models.CASCADE,
        related_name="entretiens",
        help_text="Campagne de recrutement associée."
    )
    type = models.CharField(
        max_length=50,
        choices=Type.choices,
        default=Type.TECHNIQUE,
        help_text="Type d'entretien (Technique, Motivation, Final)."
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.PLANIFIE,
        help_text="Statut actuel de la session d'entretien."
    )
    date = models.DateField(help_text="Date de la session d'entretiens.")
    heure_debut = models.TimeField(help_text="Heure de début de la session.")
    heure_fin = models.TimeField(
        null=True,
        blank=True,
        help_text="Heure de fin estimée de la session."
    )
    duree_minutes = models.PositiveIntegerField(
        default=45,
        help_text="Durée moyenne d'un passage en minutes."
    )
    lieu = models.CharField(
        max_length=255,
        default="Simplon Sénégal",
        help_text="Lieu physique ou mention de visio-conférence."
    )
    lien_visio = models.URLField(
        max_length=500,
        blank=True,
        default="",
        help_text="Lien de réunion en ligne (Google Meet, Teams, Zoom, etc.)."
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Objectifs, critères d'évaluation et consignes pour les jurys."
    )
    jurys = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="entretiens_assignes",
        blank=True,
        help_text="Membres du jury assignés à cette session d'entretien."
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "heure_debut"]
        verbose_name = "Session d'entretien"
        verbose_name_plural = "Sessions d'entretien"

    def __str__(self):
        return f"Entretien {self.get_type_display()} - {self.campagne.title} ({self.date})"

    @property
    def score_total(self):
        """Calcule le score total de l'entretien en fonction des réponses des jurys."""
        result = ReponseEntretien.objects.filter(entretien=self).aggregate(total=Sum("note"))
        return result["total"] or 0


class CreneauEntretien(models.Model):
    """
    Créneau horaire spécifique alloué à un candidat lors d'une session d'entretien,
    avec affectation des membres du jury concernés.
    """

    class Statut(models.TextChoices):
        DISPONIBLE = "DISPONIBLE", "Disponible"
        RESERVE = "RESERVE", "Réservé"
        CONFIRME = "CONFIRME", "Confirmé"
        TERMINE = "TERMINE", "Terminé"
        ANNULE = "ANNULE", "Annulé"

    entretien = models.ForeignKey(
        Entretien,
        on_delete=models.CASCADE,
        related_name="creneaux",
        help_text="Session d'entretien parente."
    )
    candidature = models.ForeignKey(
        "candidature.Candidature",
        on_delete=models.CASCADE,
        related_name="creneaux_entretien",
        null=True,
        blank=True,
        help_text="Candidat assigné à ce créneau horaire."
    )
    date = models.DateField(
        null=True,
        blank=True,
        help_text="Date spécifique si différente de la session parente."
    )
    heure_debut = models.TimeField(help_text="Heure de début du passage.")
    heure_fin = models.TimeField(help_text="Heure de fin du passage.")
    jurys = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="creneaux_jury",
        blank=True,
        help_text="Membres du jury affectés spécifiquement à ce créneau."
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.RESERVE,
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["heure_debut"]
        verbose_name = "Créneau d'entretien"
        verbose_name_plural = "Créneaux d'entretien"

    def __str__(self):
        cand_str = f" - {self.candidature.prenom} {self.candidature.nom}" if self.candidature else ""
        return f"{self.heure_debut.strftime('%H:%M')} - {self.heure_fin.strftime('%H:%M')}{cand_str}"

    @property
    def effective_date(self):
        return self.date or self.entretien.date

    @property
    def effective_jurys(self):
        """Retourne les jurys du créneau ou par défaut ceux de la session."""
        jurys = list(self.jurys.all())
        if not jurys:
            jurys = list(self.entretien.jurys.all())
        return jurys


class ConvocationEntretien(models.Model):
    """
    Convocation officielle émise pour un candidat suite à la confirmation de la session d'entretien.
    Permet au candidat de consulter ses informations de passage (espace candidat)
    et archive l'envoi de l'email de convocation.
    """

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        CONFIRME = "confirme", "Confirmé"
        PRESENT = "present", "Présent"
        ABSENT = "absent", "Absent"
        TERMINE = "termine", "Terminé"
        ANNULE = "annule", "Annulé"

    entretien = models.ForeignKey(
        Entretien,
        on_delete=models.CASCADE,
        related_name="convocations",
        help_text="Session d'entretien."
    )
    candidature = models.ForeignKey(
        "candidature.Candidature",
        on_delete=models.CASCADE,
        related_name="convocations_entretien",
        help_text="Candidature convoquée."
    )
    creneau = models.ForeignKey(
        CreneauEntretien,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="convocations",
        help_text="Créneau horaire exact attribué."
    )
    type = models.CharField(
        max_length=50,
        choices=Entretien.Type.choices,
        default=Entretien.Type.TECHNIQUE,
    )
    date = models.DateField(help_text="Date de l'entretien.")
    heure_debut = models.TimeField(help_text="Heure de début de l'entretien.")
    heure_fin = models.TimeField(null=True, blank=True, help_text="Heure de fin de l'entretien.")
    lieu = models.CharField(max_length=255, default="Simplon Sénégal")
    lien_visio = models.URLField(max_length=500, blank=True, default="")
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.CONFIRME,
    )
    date_envoi = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date et heure effectives d'envoi de la convocation par email."
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "heure_debut"]
        constraints = [
            models.UniqueConstraint(
                fields=["entretien", "candidature"],
                name="unique_candidature_par_entretien"
            )
        ]
        verbose_name = "Convocation à un entretien"
        verbose_name_plural = "Convocations aux entretiens"

    def __str__(self):
        return f"Convocation {self.get_type_display()} - {self.candidature.prenom} {self.candidature.nom} ({self.date} à {self.heure_debut.strftime('%H:%M')})"


class QuestionEntretien(models.Model):
    """
    Question d'entretien créée par l'administrateur pour une campagne.
    Les questions sont associées aux entretiens planifiés de la campagne.
    """

    class TypeQuestion(models.TextChoices):
        TEXT = "TEXT", "Texte court"
        TEXTAREA = "TEXTAREA", "Texte long"
        NOTE = "NOTE", "Note"
        COMMENTAIRE = "COMMENTAIRE", "Commentaire"
        CHOIX_UNIQUE = "CHOIX_UNIQUE", "Choix unique"
        CHOIX_MULTIPLE = "CHOIX_MULTIPLE", "Choix multiple"

    campagne = models.ForeignKey(
        "campagne.Campagne",
        on_delete=models.CASCADE,
        related_name="questions_entretien",
        help_text="Campagne de recrutement associée."
    )
    entretiens = models.ManyToManyField(
        "entretien.Entretien",
        related_name="questions_entretien",
        blank=True,
        help_text="Sessions d'entretien auxquelles cette question est associée."
    )
    intitule = models.CharField(max_length=255, help_text="Intitulé de la question.")
    type_question = models.CharField(
        max_length=30,
        choices=TypeQuestion.choices,
        default=TypeQuestion.TEXT,
        help_text="Type de réponse attendue."
    )
    ordre = models.PositiveIntegerField(default=0, help_text="Ordre d'affichage des questions.")
    obligatoire = models.BooleanField(default=False, help_text="Question obligatoire.")
    note_max = models.PositiveIntegerField(default=10, help_text="Note maximale attribuable.")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["ordre", "id"]
        verbose_name = "Question d'entretien"
        verbose_name_plural = "Questions d'entretien"

    def __str__(self):
        return self.intitule


class ReponseEntretien(models.Model):
    """
    Réponse d'un jury à une question lors d'un entretien donné.
    """

    entretien = models.ForeignKey(
        "entretien.Entretien",
        on_delete=models.CASCADE,
        related_name="reponses_entretien",
        help_text="Session d'entretien concernée."
    )
    question = models.ForeignKey(
        "entretien.QuestionEntretien",
        on_delete=models.CASCADE,
        related_name="reponses",
        help_text="Question à laquelle le jury répond."
    )
    jury = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reponses_jury",
        help_text="Membre du jury qui a répondu."
    )
    reponse = models.TextField(blank=True, default="", help_text="Réponse textuelle du jury.")
    note = models.PositiveIntegerField(null=True, blank=True, help_text="Note attribuée par le jury.")
    commentaire = models.TextField(blank=True, default="", help_text="Commentaire du jury.")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["entretien", "question", "jury"],
                name="unique_reponse_entretien_question_jury"
            )
        ]
        ordering = ["question__ordre", "question__id"]
        verbose_name = "Réponse d'entretien"
        verbose_name_plural = "Réponses d'entretien"

    def __str__(self):
        return f"Réponse de {self.jury} à {self.question} ({self.entretien})"
