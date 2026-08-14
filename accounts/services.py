from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .models import AuditLog, User
from .tasks import send_invitation_email_task
from .tokens import generate_invitation_token, verify_invitation_token


@transaction.atomic
def create_user_and_invite(email, role, actor, ip_address=None, user_agent=None):
    """
    Service pour créer un utilisateur et préparer son invitation.
    """
    # 1. Création de l'utilisateur
    now = timezone.now()
    
    user = User.objects.create_user(email=email, role=role, status=User.Status.INVITED, last_invited_at=now)

    # 2. Génération du token
    token = generate_invitation_token(user)

    # 3. Journalisation de l'audit (L'ordre est important, on log la création puis l'invitation)
    AuditLog.objects.create(
        actor=actor,
        action=AuditLog.Action.USER_CREATED,
        target=user.email,
        ip_address=ip_address,
        user_agent=user_agent,
        context={'assigned_role': role}
    )
    
    AuditLog.objects.create(
        actor=actor,
        action=AuditLog.Action.INVITATION_SENT,
        target=user.email,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # 4. Déclenchement de l'envoi d'email
    # send_invitation_email_task.delay(user_email=user.email, token=token)
    transaction.on_commit(
        lambda: send_invitation_email_task.delay(user_id=user.id, token=token,)
    )
    return user, token


@transaction.atomic
def resend_invitation(user, actor, ip_address=None, user_agent=None):
    """
    Service pour renvoyer une invitation.
    """
    if user.status != User.Status.INVITED:
        raise ValueError("Impossible d'inviter un compte qui n'est pas en attente d'activation.")

    # On met à jour l'heure d'invitation. 
    # Cela invalidera tous les anciens tokens de cet utilisateur !
    user.last_invited_at = timezone.now()
    user.save(update_fields=['last_invited_at'])

    new_token = generate_invitation_token(user)

    AuditLog.objects.create(
        actor=actor,
        action=AuditLog.Action.INVITATION_SENT,
        target=user.email,
        ip_address=ip_address,
        user_agent=user_agent,
        context={'resend': True}
    )

    # Déclenchement Celery
    # send_invitation_email_task.delay(user_email=user.email, token=new_token)
    transaction.on_commit(
        lambda: send_invitation_email_task.delay(user_id=user.id, token=new_token,)
    )

    return new_token


@transaction.atomic
def activate_account(token, password, ip_address=None, user_agent=None):
    """
    Service pour activer un compte.
    """
    # 1. Décodage et vérification du token
    payload = verify_invitation_token(token)
    user_id = payload.get('user_id')
    token_invited_at = payload.get('invited_at')

    # 2. Récupération de l'utilisateur
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise ValueError("Utilisateur introuvable.")

    # 3. CONTRÔLES DE SÉCURITÉ (Invalidation)
    if user.status != User.Status.INVITED:
        raise ValueError("Ce compte ne peut plus être activé ou est déjà actif.")
    
    # On compare la date stockée dans le token avec celle en base.
    # Si elles diffèrent, c'est que l'invitation a été renvoyée entre-temps : token invalide !
    if user.last_invited_at.isoformat() != token_invited_at:
        raise ValueError("Ce lien d'invitation a été révoqué car une nouvelle invitation a été envoyée.")

    # 4. Activation
    user.set_password(password)
    user.status = User.Status.ACTIVE
    user.save(update_fields=['password', 'status'])

    # 5. Audit
    AuditLog.objects.create(
        actor=user, # C'est l'utilisateur lui-même qui active son compte
        action=AuditLog.Action.ACCOUNT_ACTIVATED,
        target=user.email,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return user


def request_password_reset(email, ip_address=None, user_agent=None):
    """
    Initie la demande de réinitialisation sans révéler l'existence du compte.
    """
    try:
        user = User.objects.get(email=email, is_active=True)
    except User.DoesNotExist:
        # On ne fait rien mais la vue renverra un statut succès
        return None

    # Génération des tokens sécurisés de réinitialisation Django
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    # Déclenchement de la tâche asynchrone Celery
    from .tasks import send_password_reset_email_task
    send_password_reset_email_task.delay(user_id=user.id, uid=uid, token=token)

    AuditLog.objects.create(
        actor=user,
        action='PASSWORD_RESET_REQUESTED',
        target=user.email,
        ip_address=ip_address,
        user_agent=user_agent
    )


@transaction.atomic
def confirm_password_reset(uid, token, new_password, ip_address=None, user_agent=None):
    """
    Valide le token et applique le nouveau mot de passe.
    """
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        raise ValueError("Lien de réinitialisation invalide.")

    if not default_token_generator.check_token(user, token):
        raise ValueError("Le lien de réinitialisation est invalide ou a expiré.")

    user.set_password(new_password)
    user.save(update_fields=['password'])

    AuditLog.objects.create(
        actor=user,
        action='PASSWORD_RESET_COMPLETED',
        target=user.email,
        ip_address=ip_address,
        user_agent=user_agent
    )

    return user
