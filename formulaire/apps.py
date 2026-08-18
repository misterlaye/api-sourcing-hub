from django.apps import AppConfig


class FormulaireConfig(AppConfig):
    """
    Configuration de l'application formulaire.
    """

    # Utilisation d'un identifiant entier automatique
    # pour la clé primaire des modèles.
    default_auto_field = "django.db.models.BigAutoField"

    # Nom technique de l'application Django.
    name = "formulaire"

    # Nom affiché dans l'administration Django.
    verbose_name = "Formulaires"