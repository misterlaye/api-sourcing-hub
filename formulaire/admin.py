from django.contrib import admin
from .models import ( Formulaire,SectionFormulaire,Question,OptionQuestion, ReponseQuestion, ReponseOption,)


class SectionFormulaireInline(admin.TabularInline):
    model = SectionFormulaire
    extra = 1


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1


class OptionQuestionInline(admin.TabularInline):
    model = OptionQuestion
    extra = 1


class ReponseOptionInline(admin.TabularInline):
    model = ReponseOption
    extra = 0


class ReponseQuestionInline(admin.TabularInline):
    model = ReponseQuestion
    extra = 0


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
    inlines = [SectionFormulaireInline]


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
    inlines = [QuestionInline]


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
    )
    ordering = (
        "section",
        "ordre",
    )
    inlines = [OptionQuestionInline]


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


@admin.register(ReponseQuestion)
class ReponseQuestionAdmin(admin.ModelAdmin):
    """
    Configuration des réponses dans Django Admin.
    """
    list_display = (
        "id",
        "candidature",
        "question",
        "valeur",
        "date_reponse",
    )
    list_filter = (
        "candidature",
        "question",
    )
    search_fields = (
        "valeur",
        "candidature__nom",
        "candidature__prenom",
        "question__texte",
    )
    ordering = (
        "-date_reponse",
    )
    inlines = [ReponseOptionInline]


@admin.register(ReponseOption)
class ReponseOptionAdmin(admin.ModelAdmin):
    """
    Configuration des options sélectionnées dans Django Admin.
    """
    list_display = (
        "id",
        "reponse",
        "option",
    )
    list_filter = (
        "reponse__candidature",
        "option__question",
    )
    search_fields = (
        "option__texte",
        "option__valeur",
        "reponse__valeur",
    )
    ordering = (
        "reponse",
        "option",
    )
