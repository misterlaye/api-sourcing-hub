from django.contrib import admin
from django.forms import forms
from .models import Referentiel, Campagne, CritereSelection, ReunionInformation

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

@admin.register(ReunionInformation)
class ReunionInformationModelAdmin(admin.ModelAdmin):
    list_display = ('ri_date', 'begin_hour', 'end_hour','location', 'campagne')