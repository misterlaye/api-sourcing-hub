from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .jwt_views import (
    JWTLoginView as LoginView,
)
from .jwt_views import (
    LogoutView,
)
from .views import (
    ActivateAccountView,
    AdminCreateUserView,
    CompleteProfileView,
    ConfirmPasswordResetView,
    RequestPasswordResetView,
)

app_name = 'accounts'

urlpatterns = [
    # Création / Invitation d'un utilisateur par un ADMIN
    path('users/', AdminCreateUserView.as_view(), name='user-invite'),
    
    # Activation du compte avec le token
    path('activate/', ActivateAccountView.as_view(), name='account-activate'),
    
    # Complétion du profil utilisateur
    path('profile/complete/', CompleteProfileView.as_view(), name='profile-complete'),
    
    # Demande de réinitialisation de mot de passe
    path('password-reset/', RequestPasswordResetView.as_view(), name='password-reset-request'),
    
    # Confirmation du nouveau mot de passe (uid et token passés dans l'URL)
    path('password-reset/confirm/<str:uid>/<str:token>/', ConfirmPasswordResetView.as_view(), name='password-reset-confirm'),

    # Auth
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
