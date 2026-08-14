from django.urls import path

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
]
