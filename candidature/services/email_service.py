import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from .pdf_service import generate_convocation_pdf

logger = logging.getLogger(__name__)


def send_convocation_email(convocation):
    """
    Envoie un email au candidat avec en pièce jointe la convocation PDF contenant son QR code unique.
    """
    candidature = convocation.candidature
    if hasattr(convocation, "reunion_information"):
        ri = convocation.reunion_information
        campagne = ri.campagne
        date_str = ri.date.strftime("%d/%m/%Y") if hasattr(ri.date, "strftime") else str(ri.date)
        lieu_str = ri.lieu
        if convocation.creneau:
            h_deb = str(convocation.creneau.heure_debut)[:5]
            h_fin = f" à {str(convocation.creneau.heure_fin)[:5]}" if convocation.creneau.heure_fin else ""
            heure_str = f"{h_deb}{h_fin}"
            if convocation.creneau.nom:
                heure_str = f"{convocation.creneau.nom} ({heure_str})"
        else:
            heure_str = "Selon planning"
    else:
        campagne = convocation.campagne
        date_str = convocation.date.strftime("%d/%m/%Y") if hasattr(convocation.date, "strftime") else str(convocation.date)
        heure_str = str(convocation.heure_debut)[:5]
        if convocation.heure_fin:
            heure_str += f" à {str(convocation.heure_fin)[:5]}"
        lieu_str = getattr(convocation, "lieu", "Simplon Sénégal")

    subject = f"Convocation à la réunion d'information - {campagne.title}"

    body = f"""Bonjour {candidature.prenom} {candidature.nom},

Vous êtes convoqué(e) à la réunion d'information concernant la campagne :

{campagne.title}

Date :
{date_str}

Créneau / Heure :
{heure_str}

Lieu :
{lieu_str}

Veuillez présenter le QR code présent dans votre convocation à votre arrivée.
Ce QR code est unique et personnel.

Cordialement,

L'équipe SOURCING HUB
"""

    # Génération du PDF
    pdf_bytes = generate_convocation_pdf(convocation)

    filename = f"Convocation_RI_{candidature.nom}_{candidature.prenom}.pdf"
    # Nettoyage des caractères spéciaux dans le nom de fichier
    filename = filename.replace(" ", "_").replace("/", "-")

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact@sourcinghub.com")

    # Envoyer un email avec alternative HTML (Brevo requiert du contenu HTML)
    html_body = body.replace('\n', '<br/>')

    email = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[candidature.email],
    )
    email.attach_alternative(html_body, "text/html")
    email.attach(filename, pdf_bytes, "application/pdf")

    try:
        email.send(fail_silently=False)
        logger.info(f"Convocation RI envoyée avec succès à {candidature.email}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email de convocation à {candidature.email}: {e}")
        return False
