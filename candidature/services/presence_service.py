import uuid
from django.utils import timezone
from candidature.models import Candidature, Convocation, ConvocationRI
from campagne.models import ReunionInformation


def valider_presence_par_qr(qr_token_str, reunion_id=None, campagne_id=None):
    """
    Service métier de validation d'un scan QR code lors de la Réunion d'Information (RI).

    Vérifications effectuées côté backend :
    1. Le QR token existe et est un UUID valide.
    2. Le QR token correspond à une ConvocationRI (ou Candidature/Convocation).
    3. La convocation appartient bien à la Réunion d'Information (reunion_id) concernée.
    4. Vérification si le candidat est déjà marqué présent (anti-doublon).
    5. Mise à jour de la présence : statut ABSENT -> PRESENT, date_presence = now.
    """
    # 1. Validation du format token
    if not qr_token_str:
        return {
            "success": False,
            "message": "QR code invalide ou inconnu.",
        }

    cleaned_token = str(qr_token_str).strip()
    try:
        token_uuid = uuid.UUID(cleaned_token)
    except (ValueError, AttributeError):
        return {
            "success": False,
            "message": "QR code invalide ou inconnu.",
        }

    # 2. Recherche prioritaire dans ConvocationRI
    convocation_ri = (
        ConvocationRI.objects.select_related(
            "candidature", "reunion_information", "reunion_information__campagne", "creneau"
        )
        .filter(token=token_uuid)
        .first()
    )

    # Si pas trouvé par token de ConvocationRI, chercher par qr_token de Candidature
    if not convocation_ri:
        candidature = Candidature.objects.select_related("campagne").filter(qr_token=token_uuid).first()
        if candidature:
            # Chercher ou créer une ConvocationRI pour cette réunion si elle existe
            if reunion_id:
                convocation_ri = (
                    ConvocationRI.objects.select_related(
                        "candidature", "reunion_information", "reunion_information__campagne", "creneau"
                    )
                    .filter(candidature=candidature, reunion_information_id=reunion_id)
                    .first()
                )
            elif campagne_id:
                convocation_ri = (
                    ConvocationRI.objects.select_related(
                        "candidature", "reunion_information", "reunion_information__campagne", "creneau"
                    )
                    .filter(candidature=candidature, reunion_information__campagne_id=campagne_id)
                    .first()
                )
            else:
                convocation_ri = (
                    ConvocationRI.objects.select_related(
                        "candidature", "reunion_information", "reunion_information__campagne", "creneau"
                    )
                    .filter(candidature=candidature)
                    .first()
                )

    if not convocation_ri:
        # Recherche éventuelle dans Convocation legacy
        legacy_conv = Convocation.objects.select_related("candidature", "campagne").filter(
            candidature__qr_token=token_uuid, type=Convocation.Type.RI
        ).first()
        if not legacy_conv:
            return {
                "success": False,
                "message": "QR code invalide ou inconnu.",
            }
        candidature = legacy_conv.candidature
        campagne = legacy_conv.campagne
        
        # Vérification si déjà présent
        if legacy_conv.statut == Convocation.Statut.PRESENT or candidature.status == Candidature.Status.PRESENT:
            return {
                "success": True,
                "already_present": True,
                "message": "Ce candidat est déjà marqué présent.",
                "candidate": {
                    "id": candidature.id,
                    "nom": candidature.nom,
                    "prenom": candidature.prenom,
                    "email": candidature.email,
                },
                "creneau": {
                    "nom": "Créneau standard",
                    "heure_debut": str(legacy_conv.heure_debut)[:5] if legacy_conv.heure_debut else "",
                    "heure_fin": str(legacy_conv.heure_fin)[:5] if legacy_conv.heure_fin else "",
                },
                "statut": "PRESENT",
                "presence_at": legacy_conv.presence_at.isoformat() if legacy_conv.presence_at else None,
            }

        now = timezone.now()
        legacy_conv.statut = Convocation.Statut.PRESENT
        legacy_conv.presence_at = now
        legacy_conv.save()
        candidature.status = Candidature.Status.PRESENT
        candidature.save()

        return {
            "success": True,
            "already_present": False,
            "message": "Présence enregistrée avec succès",
            "candidate": {
                "id": candidature.id,
                "nom": candidature.nom,
                "prenom": candidature.prenom,
                "email": candidature.email,
            },
            "creneau": {
                "nom": "Créneau standard",
                "heure_debut": str(legacy_conv.heure_debut)[:5] if legacy_conv.heure_debut else "",
                "heure_fin": str(legacy_conv.heure_fin)[:5] if legacy_conv.heure_fin else "",
            },
            "statut": "PRESENT",
            "presence_at": now.isoformat(),
        }

    candidature = convocation_ri.candidature
    reunion = convocation_ri.reunion_information
    creneau = convocation_ri.creneau

    # 3. Vérification de la Réunion d'Information
    if reunion_id:
        try:
            if int(reunion.id) != int(reunion_id):
                return {
                    "success": False,
                    "message": "Ce QR code n'appartient pas à cette réunion d'information.",
                }
        except (ValueError, TypeError):
            pass

    if campagne_id:
        try:
            if int(reunion.campagne_id) != int(campagne_id):
                return {
                    "success": False,
                    "message": f"Ce candidat appartient à une autre campagne ({reunion.campagne.title}).",
                }
        except (ValueError, TypeError):
            pass

    creneau_data = {
        "id": creneau.id if creneau else None,
        "nom": (creneau.nom if creneau and creneau.nom else "Créneau standard"),
        "heure_debut": (str(creneau.heure_debut)[:5] if creneau else ""),
        "heure_fin": (str(creneau.heure_fin)[:5] if creneau and creneau.heure_fin else ""),
    }

    # 4. Vérification si déjà présent (Double scan)
    if convocation_ri.statut == ConvocationRI.StatutPresence.PRESENT:
        return {
            "success": True,
            "already_present": True,
            "message": "Ce candidat est déjà marqué présent.",
            "candidate": {
                "id": candidature.id,
                "nom": candidature.nom,
                "prenom": candidature.prenom,
                "email": candidature.email,
                "telephone": candidature.telephone,
            },
            "creneau": creneau_data,
            "statut": "PRESENT",
            "presence_at": convocation_ri.date_presence.isoformat() if convocation_ri.date_presence else None,
        }

    # 5. Enregistrement de la présence (ABSENT -> PRESENT)
    now = timezone.now()
    convocation_ri.statut = ConvocationRI.StatutPresence.PRESENT
    convocation_ri.date_presence = now
    convocation_ri.save()

    candidature.status = Candidature.Status.PRESENT
    candidature.save()

    return {
        "success": True,
        "already_present": False,
        "message": "Présence enregistrée avec succès",
        "candidate": {
            "id": candidature.id,
            "nom": candidature.nom,
            "prenom": candidature.prenom,
            "email": candidature.email,
            "telephone": candidature.telephone,
        },
        "creneau": creneau_data,
        "statut": "PRESENT",
        "presence_at": now.isoformat(),
    }

