import logging
from django.utils import timezone
from candidature.models import Convocation, Candidature, ConvocationRI
from campagne.models import ReunionInformation, CreneauRI
from .email_service import send_convocation_email

logger = logging.getLogger(__name__)


def creer_ou_mettre_a_jour_convocation_ri(candidature, reunion_information, creneau=None, send_email=True):
    """
    Crée ou met à jour une ConvocationRI pour un candidat, lui assigne son créneau,
    et lui envoie son PDF contenant son QR code unique par email si demandé.
    """
    convocation, created = ConvocationRI.objects.get_or_create(
        candidature=candidature,
        reunion_information=reunion_information,
        defaults={
            "creneau": creneau,
            "statut": ConvocationRI.StatutPresence.ABSENT,
        },
    )

    if not created:
        if creneau is not None:
            convocation.creneau = creneau
        convocation.save()

    if send_email:
        sent = send_convocation_email(convocation)
        if sent:
            convocation.date_envoi = timezone.now()
            convocation.save(update_fields=["date_envoi"])

    return convocation


def creer_convocations_ri_en_lot(reunion_information, candidature_ids, creneau_id=None, send_email=True):
    """
    Crée / met à jour les convocations RI pour une liste d'identifiants de candidatures,
    les assigne au créneau indiqué et déclenche l'envoi d'emails.
    """
    creneau = None
    if creneau_id:
        creneau = CreneauRI.objects.filter(id=creneau_id, reunion=reunion_information).first()

    candidatures = Candidature.objects.filter(
        id__in=candidature_ids,
        campagne=reunion_information.campagne,
    )

    resultats = []
    nb_envoyes = 0

    for candidature in candidatures:
        convocation = creer_ou_mettre_a_jour_convocation_ri(
            candidature=candidature,
            reunion_information=reunion_information,
            creneau=creneau,
            send_email=send_email,
        )
        if convocation.date_envoi:
            nb_envoyes += 1
        resultats.append(convocation)

    return {
        "total": len(resultats),
        "envoyes": nb_envoyes,
        "convocations": resultats,
    }


def creer_convocation_ri(candidature, date, heure_debut, heure_fin=None, lieu="Simplon Sénégal", send_email=True):
    """
    Fonction legacy pour compatibilité avec l'ancien modèle Convocation.
    """
    convocation = Convocation.objects.create(
        candidature=candidature,
        campagne=candidature.campagne,
        type=Convocation.Type.RI,
        date=date,
        heure_debut=heure_debut,
        heure_fin=heure_fin,
        lieu=lieu,
        statut=Convocation.Statut.EN_ATTENTE,
    )

    if send_email:
        send_convocation_email(convocation)

    return convocation

