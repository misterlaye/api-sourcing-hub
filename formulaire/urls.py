from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ( FormulaireViewSet, SectionFormulaireViewSet, QuestionViewSet, OptionQuestionViewSet, ReponseQuestionViewSet, ReponseOptionViewSet, CandidatureReponsesView,)
# Création du routeur Django REST Framework.
router = DefaultRouter()
# Gestion des formulaires.
router.register(r"formulaires",FormulaireViewSet,basename="formulaire",)
# Gestion des sections.
router.register(r"sections", SectionFormulaireViewSet, basename="section-formulaire",)
# Gestion des questions.
router.register( r"questions", QuestionViewSet,basename="question",)
# Gestion des options.
router.register( r"options", OptionQuestionViewSet,basename="option-question",)
# Gestion des réponses.
router.register(r"reponses-questions", ReponseQuestionViewSet, basename="reponse-question",)
router.register(r"reponses-options", ReponseOptionViewSet, basename="reponse-option",)
# URLs générées automatiquement par DRF.
urlpatterns = router.urls + [
    path("candidatures/<int:candidature_id>/reponses/", CandidatureReponsesView.as_view({"get": "list"}), name="candidature-reponses"),
]
