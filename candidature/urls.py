from rest_framework.routers import DefaultRouter
from .views import CandidatureCreateViewSet, CandidatureAdminViewSet

router = DefaultRouter()
router.register(r"candidatures", CandidatureCreateViewSet, basename="candidature-create")
router.register(r"admin/candidatures", CandidatureAdminViewSet, basename="candidature-admin")

urlpatterns = router.urls