from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ReferentielViewSet, CampagneViewSet, CritereSelectionViewSet

router = DefaultRouter()
router.register("referentiels", ReferentielViewSet, basename="referentiel")
router.register("campagnes", CampagneViewSet, basename="campagne")
router.register("criteres", CritereSelectionViewSet, basename="critere")

urlpatterns = [
    path("", include(router.urls)),
]