from django.core import signing
from django.utils.translation import gettext_lazy as _

# Un salt spécifique pour cette action. 
# Si un token est signé ailleurs dans l'app avec un autre salt, il ne marchera pas ici.
INVITATION_SALT = 'accounts.invitation.salt'

def generate_invitation_token(user):
    """
    Génère un token crypté contenant l'ID du user et la date d'invitation.
    """
    if not user.last_invited_at:
        raise ValueError("L'utilisateur doit avoir une date d'invitation (last_invited_at).")

    # On embarque l'ID et la date précise d'invitation
    payload = {
        'user_id': user.id,
        'invited_at': user.last_invited_at.isoformat() 
    }
    
    # dumps va sérialiser le dictionnaire en JSON, le compresser (optionnel), 
    # et le signer avec la SECRET_KEY de Django + notre sel.
    return signing.dumps(payload, salt=INVITATION_SALT)


def verify_invitation_token(token, max_age=86400 * 7):
    """
    Vérifie le token. max_age par défaut : 7 jours (en secondes).
    Retourne le payload si valide, lève une exception sinon.
    """
    try:
        # loads vérifie la signature ET l'expiration
        payload = signing.loads(token, salt=INVITATION_SALT, max_age=max_age)
        return payload
    except signing.SignatureExpired:
        raise ValueError(_("Le lien d'invitation a expiré."))
    except signing.BadSignature:
        raise ValueError(_("Le lien d'invitation est invalide ou corrompu."))
