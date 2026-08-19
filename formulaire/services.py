from django.db import transaction

from .models import (
    Formulaire,
    Question,
)

@transaction.atomic
def publier_formulaire(formulaire):
    """
    Publie un formulaire après avoir vérifié
    qu'il est correctement configuré.
    """

    # Récupérer toutes les sections du formulaire.
    sections = formulaire.sections.all()

    # Un formulaire doit avoir au moins une section.
    if not sections.exists():
        raise ValueError(
            "Le formulaire doit contenir au moins une section."
        )

    # Récupérer toutes les questions du formulaire.
    questions = Question.objects.filter(section__formulaire=formulaire )

    # Le formulaire doit avoir au moins une question.
    if not questions.exists():
        raise ValueError(
            "Le formulaire doit contenir au moins une question."
        )

    # Types de questions qui nécessitent des options.
    types_avec_options = [
        Question.TypeQuestion.RADIO,
        Question.TypeQuestion.CHECKBOX,
        Question.TypeQuestion.SELECT,
    ]

    # Vérifier chaque question.
    for question in questions:

        # Si la question nécessite des options...
        if question.type_question in types_avec_options:

            # Compter les options.
            nombre_options = question.options.count()

            # Une question à choix doit avoir au moins
            # deux options.
            if nombre_options < 2:
                raise ValueError(
                    f"La question « {question.texte} » "
                    "doit avoir au moins deux options."
                )

    # Toutes les vérifications sont terminées.
    formulaire.publier = True
    formulaire.actif = True

    formulaire.save(
        update_fields=[
            "publier",
            "actif",
            "updated_at",
        ]
    )

    return formulaire


@transaction.atomic
def depublier_formulaire(formulaire):
    """
    Dépublie un formulaire.
    """

    formulaire.publier = False

    formulaire.save(
        update_fields=[
            "publier",
            "updated_at",
        ]
    )

    return formulaire