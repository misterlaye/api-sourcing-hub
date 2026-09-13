from rest_framework.permissions import BasePermission

from .models import User


class IsAccountActive(BasePermission):
    """
    Vérifie que l'utilisateur est authentifié ET que son compte est dans l'état ACTIVE.
    Bloque immédiatement les comptes INVITED ou SUSPENDED, même s'ils ont un JWT valide.
    """
    message = "Votre compte n'est pas actif ou a été suspendu."

    def has_permission(self, request, view):
        return bool(
            request.user 
            and request.user.is_authenticated 
            and request.user.can_login
        )


class IsProfileComplete(BasePermission):
    """
    Exige que l'utilisateur ait complété son profil obligatoire lors de la 1ère connexion.
    """
    message = "Vous devez compléter votre profil avant d'accéder à cette ressource."

    def has_permission(self, request, view):
        # On laisse passer la requête si l'utilisateur est sur la route de mise à jour du profil
        if getattr(view, 'is_profile_completion_view', False):
            return True
            
        return bool(
            request.user 
            and request.user.is_authenticated 
            and request.user.is_profile_complete
        )


class HasRole(BasePermission):
    """
    Permission générique par rôle.
    Usage dans une vue DRF :
        permission_classes = [IsAccountActive, HasRole.with_roles(User.Role.ADMIN, User.Role.JURY)]
    """
    allowed_roles = []

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in self.allowed_roles

    @classmethod
    def with_roles(cls, *roles):
        """Fabrique de classe pour spécifier les rôles autorisés de façon fluide."""
        class DynamicRolePermission(cls):
            allowed_roles = roles
        return DynamicRolePermission
