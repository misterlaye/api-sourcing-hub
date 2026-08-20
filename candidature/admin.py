from django.contrib import admin

from .models import Candidature, Convocation
from formulaire.models import ReponseQuestion, ReponseOption


class ReponseOptionInline(admin.TabularInline):
    model = ReponseOption
    extra = 0


class ReponseQuestionInline(admin.TabularInline):
    model = ReponseQuestion
    extra = 0


class ConvocationInline(admin.TabularInline):
    model = Convocation
    extra = 0
    readonly_fields = ("qr_token", "presence_at", "date_creation")


@admin.register(Candidature)
class CandidatureAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nom",
        "prenom",
        "email",
        "campagne",
        "status",
        "qr_token",
        "date_soumission",
    )
    list_filter = (
        "campagne",
        "status",
    )
    search_fields = (
        "nom",
        "prenom",
        "email",
        "qr_token",
    )
    readonly_fields = ("qr_token", "date_soumission")
    ordering = ("-date_soumission",)
    inlines = [ConvocationInline, ReponseQuestionInline]


@admin.register(Convocation)
class ConvocationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "candidature",
        "campagne",
        "type",
        "date",
        "heure_debut",
        "lieu",
        "statut",
        "presence_at",
    )
    list_filter = (
        "type",
        "statut",
        "campagne",
        "date",
    )
    search_fields = (
        "candidature__nom",
        "candidature__prenom",
        "candidature__email",
        "candidature__qr_token",
    )
    readonly_fields = ("presence_at", "date_creation", "date_modification")
