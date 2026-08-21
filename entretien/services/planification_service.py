import logging
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from entretien.models import Entretien, CreneauEntretien, ConvocationEntretien, QuestionEntretien
from .email_service import (
    envoyer_email_convocation_candidat,
    envoyer_email_planning_jury,
)

logger = logging.getLogger(__name__)


def associer_questions_entretien(entretien: Entretien):
    """Associe les questions de la campagne à l'entretien confirmé."""
    questions = QuestionEntretien.objects.filter(campagne=entretien.campagne)
    entretien.questions_entretien.set(questions)


def verifier_planification_entretien(entretien: Entretien):
    """
    Vérifie la validité des règles métier avant la confirmation et l'envoi des convocations :
    1. Au moins un jury est affecté (globalement ou par créneau).
    2. Au moins un candidat est planifié sur un créneau.
    3. Chaque candidat possède un créneau avec horaire valide (heure_debut < heure_fin).
    4. Chaque créneau candidat possède au moins un membre du jury affecté.
    5. Pas de doublon de candidat sur la même session.
    """
    session_jurys = list(entretien.jurys.all())
    creneaux = list(
        entretien.creneaux.select_related("candidature")
        .prefetch_related("jurys")
        .all()
    )

    # 1. Vérification des jurys globaux ou locaux
    all_assigned_jurys = set(session_jurys)
    for c in creneaux:
        all_assigned_jurys.update(c.jurys.all())

    if not all_assigned_jurys:
        raise ValidationError(
            "Impossible de confirmer : au moins un membre du jury doit être affecté à la session d'entretien."
        )

    # 2. Vérification des candidats planifiés
    creneaux_candidats = [c for c in creneaux if c.candidature_id is not None]
    if not creneaux_candidats:
        raise ValidationError(
            "Impossible de confirmer : aucun candidat n'a été planifié sur les créneaux de cette session."
        )

    # 3. Vérification des horaires et de l'affectation jury par créneau
    candidats_vus = set()
    for creneau in creneaux_candidats:
        cand = creneau.candidature
        
        # Doublon candidat
        if cand.id in candidats_vus:
            raise ValidationError(
                f"Le candidat {cand.prenom} {cand.nom} est assigné à plusieurs créneaux pour cette session."
            )
        candidats_vus.add(cand.id)

        # Horaires
        if not creneau.heure_debut or not creneau.heure_fin:
            raise ValidationError(
                f"Le créneau de {cand.prenom} {cand.nom} doit comporter une heure de début et une heure de fin."
            )
        if creneau.heure_debut >= creneau.heure_fin:
            raise ValidationError(
                f"L'heure de début ({creneau.heure_debut}) doit être antérieure à l'heure de fin ({creneau.heure_fin}) pour {cand.prenom} {cand.nom}."
            )

        # Jury pour ce créneau spécifique
        creneau_jurys = list(creneau.jurys.all()) or session_jurys
        if not creneau_jurys:
            raise ValidationError(
                f"Le créneau du candidat {cand.prenom} {cand.nom} ne possède aucun jury affecté."
            )

    return True


@transaction.atomic
def confirmer_et_envoyer_convocations(entretien: Entretien, envoyer_emails: bool = True):
    """
    Règle métier principale :
    - Vérifie la conformité de la session (créneaux, jurys, candidats).
    - Crée / met à jour les ConvocationEntretien pour chaque candidat.
    - Met à jour le statut des créneaux et de la session à CONFIRME.
    - Envoie les emails de convocation personnalisés à chaque candidat.
    - Envoie le récapitulatif du planning complet à chaque jury affecté.
    """
    # 1. Validation métier stricte
    verifier_planification_entretien(entretien)

    # 2. Récupération des créneaux candidats
    creneaux_candidats = (
        entretien.creneaux.select_related("candidature")
        .prefetch_related("jurys")
        .filter(candidature__isnull=False)
        .order_by("heure_debut")
    )

    convocations_creees = []

    # 3. Création des enregistrements de convocation
    for creneau in creneaux_candidats:
        convocation, _ = ConvocationEntretien.objects.update_or_create(
            entretien=entretien,
            candidature=creneau.candidature,
            defaults={
                "creneau": creneau,
                "type": entretien.type,
                "date": creneau.effective_date,
                "heure_debut": creneau.heure_debut,
                "heure_fin": creneau.heure_fin,
                "lieu": entretien.lieu,
                "lien_visio": entretien.lien_visio,
                "statut": ConvocationEntretien.Statut.CONFIRME,
            },
        )
        convocations_creees.append(convocation)

        # Mettre à jour le statut du créneau
        creneau.statut = CreneauEntretien.Statut.CONFIRME
        creneau.save(update_fields=["statut", "date_modification"])

    # 4. Passage du statut de l'entretien à CONFIRME
    entretien.statut = Entretien.Statut.CONFIRME
    entretien.save(update_fields=["statut", "date_modification"])

    # 4b. Association des questions de la campagne à l'entretien
    associer_questions_entretien(entretien)

    nb_emails_candidats = 0
    nb_emails_jurys = 0

    # 5. Envoi des emails aux candidats et jurys si demandé
    if envoyer_emails:
        # Envoi aux candidats
        for conv in convocations_creees:
            sent = envoyer_email_convocation_candidat(conv)
            if sent:
                conv.date_envoi = timezone.now()
                conv.save(update_fields=["date_envoi", "date_modification"])
                nb_emails_candidats += 1

        # Envoi aux jurys
        session_jurys = set(entretien.jurys.all())
        all_jurys = set(session_jurys)
        for creneau in creneaux_candidats:
            all_jurys.update(creneau.jurys.all())

        for jury in all_jurys:
            # Récupérer les créneaux concernés par ce jury
            jury_creneaux = [
                c for c in creneaux_candidats
                if jury in (list(c.jurys.all()) or list(session_jurys))
            ]
            if jury_creneaux:
                sent_jury = envoyer_email_planning_jury(jury, entretien, jury_creneaux)
                if sent_jury:
                    nb_emails_jurys += 1

    return {
        "success": True,
        "entretien_id": entretien.id,
        "statut": entretien.statut,
        "total_candidats": len(convocations_creees),
        "emails_candidats_envoyes": nb_emails_candidats,
        "total_jurys": len(all_jurys) if envoyer_emails else 0,
        "emails_jurys_envoyes": nb_emails_jurys,
        "convocations": convocations_creees,
    }
