from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrateur')
        JURY = 'JURY', _('Membre du Jury')
        CANDIDAT = 'CANDIDAT', _('Candidat')

    class Status(models.TextChoices):
        INVITED = 'INVITED', _('Invité')
        ACTIVE = 'ACTIVE', _('Actif')
        SUSPENDED = 'SUSPENDED', _('Suspendu')

    email = models.EmailField(_('adresse email'), unique=True)
    
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CANDIDAT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INVITED)
    is_profile_complete = models.BooleanField(default=False)
    
    last_invited_at = models.DateTimeField(null=True, blank=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True) 
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [] # L'email est déjà requis par USERNAME_FIELD

    def __str__(self):
        return self.email

    @property
    def can_login(self):
        """
        Un utilisateur ne peut se connecter que s'il est ACTIVE et is_active=True.
        """
        return self.status == self.Status.ACTIVE and self.is_active


class AuditLog(models.Model):
    class Action(models.TextChoices):
        USER_CREATED = 'USER_CREATED', _('Utilisateur Créé')
        INVITATION_SENT = 'INVITATION_SENT', _('Invitation Envoyée')
        ACCOUNT_ACTIVATED = 'ACCOUNT_ACTIVATED', _('Compte Activé')
        LOGIN_SUCCESS = 'LOGIN_SUCCESS', _('Connexion Réussie')
        LOGIN_FAILED = 'LOGIN_FAILED', _('Échec Connexion')
        # On en rajoutera au besoin...

    class Status(models.TextChoices):
        SUCCESS = 'SUCCESS', _('Succès')
        FAILED = 'FAILED', _('Échec')

    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='actions_performed')
    
    action = models.CharField(max_length=50, choices=Action.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUCCESS)
    
    # Qui ou quoi a été ciblé ? (Ex: L'email de l'utilisateur créé)
    target = models.CharField(max_length=255, null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    context = models.JSONField(default=dict, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.created_at}] {self.actor} -> {self.action} ({self.status})'
