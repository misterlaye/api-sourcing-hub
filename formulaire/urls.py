from rest_framework.routers import DefaultRouter

from .views import ( FormulaireViewSet, SectionFormulaireViewSet, QuestionViewSet, OptionQuestionViewSet,)
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
# URLs générées automatiquement par DRF.
urlpatterns = router.urls