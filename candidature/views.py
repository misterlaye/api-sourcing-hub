from rest_framework import viewsets, mixins, permissions
from .models import Candidature
from .serializers import CandidatureSerializer, CandidatureCreateSerializer


class CandidatureCreateViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
   

    queryset = Candidature.objects.all()
    serializer_class = CandidatureCreateSerializer
    permission_classes = [permissions.AllowAny]


class CandidatureAdminViewSet(viewsets.ModelViewSet):
   

    queryset = Candidature.objects.all()
    serializer_class = CandidatureSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        campagne_id = self.request.query_params.get("campagne")
        if campagne_id:
            queryset = queryset.filter(campagne_id=campagne_id)
        return queryset