from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditLog, User
from .permissions import HasRole, IsAccountActive, IsProfileComplete
from .serializers import (
    AccountActivationSerializer,
    AdminUserCreateSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileCompletionSerializer,
)
from .services import (
    activate_account,
    confirm_password_reset,
    create_user_and_invite,
    request_password_reset,
)


def get_client_ip(request):
    """Utilitaire basique pour récupérer l'IP"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


class AdminCreateUserView(APIView):
    """
    Endpoint réservé aux Administrateurs pour créer et inviter un compte.
    POST /api/accounts/users/
    """
    permission_classes = [IsAccountActive, HasRole.with_roles(User.Role.ADMIN)]

    def post(self, request):
        serializer = AdminUserCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        role = serializer.validated_data['role']

        try:
            user, token = create_user_and_invite(
                email=email,
                role=role,
                actor=request.user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response(
                {
                    "detail": "Utilisateur créé avec succès et invitation envoyée.",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "role": user.role,
                        "status": user.status
                    }
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class ActivateAccountView(APIView):
    """
    Endpoint: POST /api/accounts/activate/
    Permet à un utilisateur invité d'activer son compte en définissant son mot de passe.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = AccountActivationSerializer(data=request.data)
        
        serializer.is_valid(raise_exception=True) 

        token = serializer.validated_data['token']
        password = serializer.validated_data['password']
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        try:
            activate_account(token=token, password=password, ip_address=get_client_ip(request), user_agent=user_agent)
            return Response(
                {"detail": "Votre compte a été activé avec succès. Vous pouvez maintenant vous connecter."},
                status=status.HTTP_200_OK
            )
            
        except ValueError as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class CompleteProfileView(APIView):
    """
    Endpoint: PATCH /api/accounts/profile/complete/
    Permet à l'utilisateur actif de finaliser la création de son profil.
    """
    permission_classes = [IsAccountActive, IsProfileComplete]
    
    # Flag lu par la permission IsProfileComplete pour autoriser cet endpoint
    is_profile_completion_view = True

    def patch(self, request):
        serializer = ProfileCompletionSerializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        
        # Mise à jour et validation du profil
        user = serializer.save()
        user.is_profile_complete = True
        user.save(update_fields=['is_profile_complete'])

        # Log d'audit
        AuditLog.objects.create(
            actor=user,
            action='PROFILE_COMPLETED',
            target=user.email,
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return Response({
            "detail": "Profil complété avec succès. Vous avez désormais accès à l'ensemble de la plateforme.",
            "is_profile_complete": True
        }, status=status.HTTP_200_OK)


class RequestPasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        request_password_reset(
            email=serializer.validated_data['email'],
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        return Response(
            {"detail": "Si cette adresse correspond à un compte actif, un email de réinitialisation a été envoyé."},
            status=status.HTTP_202_ACCEPTED
        )


class ConfirmPasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, uid, token):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            confirm_password_reset(
                uid=uid,
                token=token,
                new_password=serializer.validated_data['new_password'],
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return Response(
                {"detail": "Votre mot de passe a été réinitialisé avec succès."},
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from .serializers import UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet d'administration pour lister, inviter, consulter et modifier les utilisateurs.
    Permet également à l'utilisateur connecté de consulter/modifier son profil via /me/.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'me':
            return [permissions.IsAuthenticated()]
        return [IsAccountActive(), HasRole.with_roles(User.Role.ADMIN)()]

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminUserCreateSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        role = serializer.validated_data['role']

        try:
            user, token = create_user_and_invite(
                email=email,
                role=role,
                actor=request.user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return Response(
                {
                    "detail": "Utilisateur créé avec succès et invitation envoyée.",
                    "user": UserSerializer(user).data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        if request.method == 'GET':
            serializer = UserSerializer(request.user)
            return Response(serializer.data)
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)


