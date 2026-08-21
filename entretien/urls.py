from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EntretienViewSet,
    CreneauEntretienViewSet,
    ConvocationEntretienViewSet,
    MesConvocationsEntretienViewSet,
    QuestionEntretienViewSet,
    ReponseEntretienViewSet,
)

app_name = "entretien"

router = DefaultRouter()
router.register("entretiens", EntretienViewSet, basename="entretien")
router.register("creneaux-entretiens", CreneauEntretienViewSet, basename="creneau-entretien")
router.register("convocations-entretiens", ConvocationEntretienViewSet, basename="convocation-entretien")
router.register("candidat/entretiens/mes-convocations", MesConvocationsEntretienViewSet, basename="mes-convocations-entretien")
router.register("questions-entretien", QuestionEntretienViewSet, basename="question-entretien")
router.register("reponses-entretien", ReponseEntretienViewSet, basename="reponse-entretien")

urlpatterns = [
    path("", include(router.urls)),
]
