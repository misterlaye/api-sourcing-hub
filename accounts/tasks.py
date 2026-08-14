from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import User


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_invitation_email_task(user_id, token):
    """
    Tâche Celery pour l'envoi asynchrone de l'invitation initiale ou du renvoi.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    activation_link = f"{settings.FRONTEND_URL}/activate?token={token}"
    
    subject = "Invitation à rejoindre la plateforme Sourcing Hub"

    message = f"""
Bonjour,

Vous avez été invité sur Sourcing Hub.

Pour activer votre compte, cliquez sur le lien suivant :

{activation_link}

Ce lien est valide pour une durée limitée.

Cordialement,
L'équipe Sourcing Hub
"""

    html_message = f"""
<html>
<body>
    <p>Bonjour,</p>

    <p>
        Vous avez été invité sur <strong>Sourcing Hub</strong>.
    </p>

    <p>
        Pour activer votre compte, cliquez sur le bouton ci-dessous :
    </p>

    <p>
        <a href="{activation_link}"
           style="
               display:inline-block;
               padding:12px 20px;
               background:#2563eb;
               color:white;
               text-decoration:none;
               border-radius:6px;
           ">
            Activer mon compte
        </a>
    </p>

    <p>
        Ou utilisez ce lien :
        <br>
        {activation_link}
    </p>

    <p>
        Ce lien est valide pour une durée limitée.
    </p>

    <p>
        Cordialement,<br>
        L'équipe Sourcing Hub
    </p>
</body>
</html>
"""
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
        using='default',
    )


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_password_reset_email_task(user_id, uid, token):
    """
    Tâche Celery pour l'envoi de réinitialisation de mot de passe.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
    
    subject = "Réinitialisation de votre mot de passe - Sourcing Hub"
    message = f"""
Bonjour,

Pour réinitialiser votre mot de passe, utilisez le lien suivant :

{reset_link}

Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email.

Cordialement,
L'équipe Sourcing Hub
"""

    html_message = f"""
<html>
<body>
    <p>Bonjour,</p>

    <p>
        Une demande de réinitialisation de votre mot de passe
        a été effectuée.
    </p>

    <p>
        Cliquez sur le bouton ci-dessous :
    </p>

    <p>
        <a href="{reset_link}"
           style="
               display:inline-block;
               padding:12px 20px;
               background:#2563eb;
               color:white;
               text-decoration:none;
               border-radius:6px;
           ">
            Réinitialiser mon mot de passe
        </a>
    </p>

    <p>
        Si vous n'êtes pas à l'origine de cette demande,
        vous pouvez ignorer cet email.
    </p>

    <p>
        Cordialement,<br>
        L'équipe Sourcing Hub
    </p>
</body>
</html>
"""
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
        using='default',
    )
