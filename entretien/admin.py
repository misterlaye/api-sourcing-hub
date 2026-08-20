from django.contrib import admin
from .models import Entretien, CreneauEntretien, ConvocationEntretien


class CreneauEntretienInline(admin.TabularInline):
    model = CreneauEntretien
    extra = 0
    filter_horizontal = ("jurys",)


class ConvocationEntretienInline(admin.TabularInline):
    model = ConvocationEntretien
    extra = 0
    readonly_fields = ("date_envoi", "date_creation")


@admin.register(Entretien)
class EntretienAdmin(admin.ModelAdmin):
    list_display = ("id", "campagne", "type", "statut", "date", "heure_debut", "heure_fin", "duree_minutes", "lieu")
    list_filter = ("type", "statut", "date", "campagne")
    search_fields = ("campagne__title", "lieu", "notes")
    filter_horizontal = ("jurys",)
    inlines = [CreneauEntretienInline, ConvocationEntretienInline]


@admin.register(CreneauEntretien)
class CreneauEntretienAdmin(admin.ModelAdmin):
    list_display = ("id", "entretien", "candidature", "date", "heure_debut", "heure_fin", "statut")
    list_filter = ("statut", "date", "entretien__campagne", "entretien__type")
    search_fields = ("candidature__nom", "candidature__prenom", "candidature__email")
    filter_horizontal = ("jurys",)


@admin.register(ConvocationEntretien)
class ConvocationEntretienAdmin(admin.ModelAdmin):
    list_display = ("id", "candidature", "entretien", "type", "date", "heure_debut", "heure_fin", "statut", "date_envoi")
    list_filter = ("type", "statut", "date", "entretien__campagne")
    search_fields = ("candidature__nom", "candidature__prenom", "candidature__email")
    readonly_fields = ("date_creation", "date_modification")
