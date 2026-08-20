from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import AuditLog
from .permissions import IsAccountActive
from .views import get_client_ip


class JWTTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extend to include user data and enforce can_login."""
    def validate(self, attrs):
        data = super().validate(attrs)
        user = getattr(self, 'user', None)
        if user is None:
            raise AuthenticationFailed('Authentication failed')
        if not user.can_login:
            raise AuthenticationFailed('Compte inactif ou non autorisé à se connecter.')
        data['user'] = {"id": user.id, "email": user.email, "role": user.role}
        return data


class JWTLoginView(TokenObtainPairView):
    """Login endpoint returning access + refresh tokens (JWT).

    POST /api/accounts/login/ -> { access, refresh, user }
    """
    permission_classes = [AllowAny]
    serializer_class = JWTTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        # Audit logging: if success, log LOGIN_SUCCESS; otherwise LOGIN_FAILED
        if response.status_code == 200:
            try:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                user = serializer.user
                from django.utils import timezone
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])

                AuditLog.objects.create(
                    actor=user,
                    action=AuditLog.Action.LOGIN_SUCCESS,
                    target=user.email,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            except Exception:
                pass
        else:
            AuditLog.objects.create(
                actor=None,
                action=AuditLog.Action.LOGIN_FAILED,
                target=request.data.get('email'),
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

        return response


class LogoutView(APIView):
    """Logout by blacklisting the provided refresh token.

    POST /api/accounts/logout/ with JSON { "refresh": "<token>" }
    Requires authenticated user (IsAccountActive).
    """
    permission_classes = [IsAccountActive]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({"detail": "Refresh token requis."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({"detail": "Token invalide ou déjà révoqué."}, status=status.HTTP_400_BAD_REQUEST)

        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.LOGOUT,
            target=request.user.email,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        return Response({"detail": "Déconnecté avec succès."}, status=status.HTTP_200_OK)
