from rest_framework.routers import DefaultRouter
from .views import (
    CandidatureCreateViewSet,
    CandidatureAdminViewSet,
    ConvocationViewSet,
    ConvocationRIViewSet,
    CandidateConvocationsViewSet,
    MesCandidaturesViewSet,
)

app_name = "candidature"

router = DefaultRouter()
router.register(r"candidatures", CandidatureCreateViewSet, basename="candidature-create")
router.register(r"admin/candidatures", CandidatureAdminViewSet, basename="candidature-admin")
router.register(r"convocations", ConvocationViewSet, basename="convocations")
router.register(r"convocations-ri", ConvocationRIViewSet, basename="convocations-ri")
router.register(r"candidat/mes-convocations", CandidateConvocationsViewSet, basename="candidat-convocations")
router.register(r"candidat/mes-candidatures", MesCandidaturesViewSet, basename="candidat-candidatures")

urlpatterns = router.urls