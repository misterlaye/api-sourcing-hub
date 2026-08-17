from django.contrib import admin
from .models import ( Formulaire,SectionFormulaire,Question,OptionQuestion,
)
@admin.register(Formulaire)
class FormulaireAdmin(admin.ModelAdmin):
    """
    Configuration du formulaire dans Django Admin.
    """
    list_display = (
        "titre",
        "campagne",
        "publier",
        "actif",
        "date_creation",
    )
    list_filter = (
        "publier",
        "actif",
    )
    search_fields = (
        "titre",
        "description",
    )
    ordering = (
        "-date_creation",
    )
@admin.register(SectionFormulaire)
class SectionFormulaireAdmin(admin.ModelAdmin):
    """
    Configuration des sections dans Django Admin.
    """
    list_display = (
        "titre",
        "formulaire",
        "ordre",
    )
    list_filter = (
        "formulaire",
    )
    search_fields = (
        "titre",
        "description",
    )
    ordering = (
        "formulaire",
        "ordre",
    )
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """
    Configuration des questions dans Django Admin.
    """
    list_display = (
        "texte",
        "section",
        "type_question",
        "obligatoire",
        "ordre",
    )
    list_filter = (
        "type_question",
        "obligatoire",
    )
    search_fields = (
        "texte",
        "description",
    )
    ordering = (
        "section",
        "ordre",
    )

@admin.register(OptionQuestion)
class OptionQuestionAdmin(admin.ModelAdmin):
    """
    Configuration des options dans Django Admin.
    """
    list_display = (
        "texte",
        "valeur",
        "question",
        "ordre",
    )
    list_filter = (
        "question",
    )
    search_fields = (
        "texte",
        "valeur",
    )
    ordering = (
        "question",
        "ordre",
    )