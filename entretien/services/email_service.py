import logging
from django.conf import settings
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)


def envoyer_email_convocation_candidat(convocation):
    """
    Envoie un email de convocation officiel et personnalisé au candidat avec les détails
    du passage, horaires, lieu / lien de visio et recommandations.
    """
    candidature = convocation.candidature
    campagne = convocation.entretien.campagne
    type_label = convocation.get_type_display()
    date_str = convocation.date.strftime("%d/%m/%Y") if hasattr(convocation.date, "strftime") else str(convocation.date)
    h_deb = convocation.heure_debut.strftime("%H:%M") if hasattr(convocation.heure_debut, "strftime") else str(convocation.heure_debut)[:5]
    h_fin = f" à {convocation.heure_fin.strftime('%H:%M')}" if (convocation.heure_fin and hasattr(convocation.heure_fin, "strftime")) else (f" à {str(convocation.heure_fin)[:5]}" if convocation.heure_fin else "")
    horaire_str = f"{h_deb}{h_fin}"

    modalite_str = convocation.lieu or "Simplon Sénégal"
    if convocation.lien_visio:
        modalite_str += f"\nLien de visioconférence : {convocation.lien_visio}"

    subject = f"Convocation à votre {type_label} - {campagne.title}"

    body = f"""Bonjour {candidature.prenom} {candidature.nom},

Nous avons le plaisir de vous informer que votre entretien pour l'étape : {type_label} dans le cadre de la campagne « {campagne.title} » est planifié.

Détails de votre convocation :
--------------------------------------------------
• Date : {date_str}
• Horaire de passage : {horaire_str}
• Modalité / Lieu : {modalite_str}
--------------------------------------------------

Consignes importantes :
- Merci de vous présenter ou de vous connecter 10 minutes avant l'heure prévue.
- Munissez-vous d'une pièce d'identité en cours de validité.
- Assurez-vous d'être dans un environnement calme favorisant l'échange.

Vous pouvez également retrouver le récapitulatif de votre convocation sur votre espace candidat en ligne.

Nous vous souhaitons un excellent entretien.

Cordialement,
L'équipe SOURCING HUB
"""

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact@sourcinghub.com")

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[candidature.email],
    )

    try:
        email.send(fail_silently=False)
        logger.info(f"Convocation à l'entretien envoyée avec succès à {candidature.email}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email de convocation à {candidature.email}: {e}")
        return False


def envoyer_email_planning_jury(jury, entretien, creneaux_jury):
    """
    Envoie le planning complet de la session aux membres du jury assignés,
    avec la liste chronologique des candidats et leurs horaires respectifs.
    """
    campagne = entretien.campagne
    type_label = entretien.get_type_display()
    date_str = entretien.date.strftime("%d/%m/%Y") if hasattr(entretien.date, "strftime") else str(entretien.date)
    jury_name = f"{jury.first_name} {jury.last_name}".strip() or jury.email

    modalite_str = entretien.lieu or "Simplon Sénégal"
    if entretien.lien_visio:
        modalite_str += f"\nLien de visioconférence : {entretien.lien_visio}"

    lignes_planning = []
    for idx, creneau in enumerate(creneaux_jury, start=1):
        cand = creneau.candidature
        cand_str = f"{cand.prenom} {cand.nom} ({cand.email} - {cand.telephone or 'N/A'})" if cand else "Créneau non attribué"
        h_deb = creneau.heure_debut.strftime("%H:%M") if hasattr(creneau.heure_debut, "strftime") else str(creneau.heure_debut)[:5]
        h_fin = creneau.heure_fin.strftime("%H:%M") if (creneau.heure_fin and hasattr(creneau.heure_fin, "strftime")) else str(creneau.heure_fin)[:5]
        lignes_planning.append(f"{idx}. [{h_deb} - {h_fin}] : {cand_str}")

    planning_str = "\n".join(lignes_planning) if lignes_planning else "Aucun créneau planifié."

    notes_str = entretien.notes if entretien.notes else "Évaluation des compétences et de la motivation selon la grille standard."

    subject = f"Planning Jury - {type_label} ({campagne.title}) - {date_str}"

    body = f"""Bonjour {jury_name},

Vous êtes assigné(e) en tant que membre du jury pour la session d'entretiens suivante :

Informations Générales :
--------------------------------------------------
• Campagne : {campagne.title}
• Type d'entretien : {type_label}
• Date : {date_str}
• Modalité / Lieu : {modalite_str}
--------------------------------------------------

Objectifs & Consignes d'évaluation :
{notes_str}

Planning de vos passages :
--------------------------------------------------
{planning_str}
--------------------------------------------------

Merci de bien vouloir vous connecter / vous présenter 15 minutes avant le début de la première session.

Cordialement,
L'équipe SOURCING HUB
"""

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact@sourcinghub.com")

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[jury.email],
    )

    try:
        email.send(fail_silently=False)
        logger.info(f"Planning jury envoyé avec succès à {jury.email}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du planning jury à {jury.email}: {e}")
        return False
