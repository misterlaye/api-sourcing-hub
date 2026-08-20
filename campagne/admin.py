from django.contrib import admin
from .models import Referentiel, Campagne, CritereSelection, ReunionInformation, CreneauRI

@admin.register(Referentiel)
class ReferentielModelAdmin(admin.ModelAdmin):
    list_display = ('title','description')

@admin.register(Campagne)
class CampagneModelAdmin(admin.ModelAdmin):
    list_display = ('title','description','begin_date', 'end_date', 'status','get_criteres')
    filter_horizontal = ('criteres',)

    def get_criteres(self, obj):
        return ", ".join(c.name for c in obj.criteres.all())
    get_criteres.short_description = "Critères"

@admin.register(CritereSelection)
class CritereSelectionModelAdmin(admin.ModelAdmin):
    list_display = ('name','description')

class CreneauRIInline(admin.TabularInline):
    model = CreneauRI
    extra = 1
    fields = ('heure_debut', 'heure_fin', 'capacite')

@admin.register(ReunionInformation)
class ReunionInformationModelAdmin(admin.ModelAdmin):
    list_display = ('titre', 'date', 'lieu', 'campagne', 'actif')
    list_filter = ('actif', 'date')
    search_fields = ('titre', 'lieu', 'campagne__title')
    inlines = [CreneauRIInline]

@admin.register(CreneauRI)
class CreneauRIModelAdmin(admin.ModelAdmin):
    list_display = ('reunion', 'heure_debut', 'heure_fin', 'capacite')
    list_filter = ('reunion',)
