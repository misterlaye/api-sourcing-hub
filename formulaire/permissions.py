from rest_framework.permissions import BasePermission

class IsAdministrateur(BasePermission):
    message=("Vous devez etre administrateur pour effectuer cette operation")

    def has_permission(self, request, view):
        if request.method in [
            "GET",
            "HEAD",
            "OPTIONS"
        ]:
            return bool(
                request.user and request.user.is_authenticated
            )
        # Pour les operations d ecriture 
        # is_staff est la permission standard Django.
        if getattr(request.user,"is_staff", False):
            return True 
        # on accepte également le rôle administrateur.
        role= getattr(request.user,"role",None)
        if role:
            return str(role).lower()in[
                "admin",
                "administrateur",
            ]
        return False

