from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ReferentielViewSet, CampagneViewSet, CritereSelectionViewSet, ReunionInformationViewSet

router = DefaultRouter()
router.register("referentiels", ReferentielViewSet, basename="referentiel")
router.register("campagnes", CampagneViewSet, basename="campagne")
router.register("criteres", CritereSelectionViewSet, basename="critere")
router.register("reunions", ReunionInformationViewSet, basename="reunion")

urlpatterns = [
    path("", include(router.urls)),
]