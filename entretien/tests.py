from datetime import date, time
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from campagne.models import Campagne, Referentiel
from candidature.models import Candidature
from entretien.models import Entretien, CreneauEntretien, ConvocationEntretien, QuestionEntretien, ReponseEntretien
from entretien.services import (
    verifier_planification_entretien,
    confirmer_et_envoyer_convocations,
)


class EntretienMetierTests(TestCase):
    """Tests unitaires des règles métier de planification et confirmation d'entretiens."""

    def setUp(self):
        self.referentiel = Referentiel.objects.create(
            title="Développement Web & IA",
            description="Référentiel compétences web & IA"
        )
        self.campagne = Campagne.objects.create(
            title="Promotion Dev Web IA 2026",
            description="Campagne de recrutement",
            begin_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=Campagne.Status.PUBLIEE,
            referentiel=self.referentiel,
        )

        self.jury1 = User.objects.create_user(
            email="jury1@simplon.sn",
            first_name="Marcus",
            last_name="Thorne",
            role=User.Role.JURY,
            status=User.Status.ACTIVE,
        )
        self.jury2 = User.objects.create_user(
            email="jury2@simplon.sn",
            first_name="Lisa",
            last_name="Cooper",
            role=User.Role.JURY,
            status=User.Status.ACTIVE,
        )

        self.candidat1 = Candidature.objects.create(
            campagne=self.campagne,
            nom="Diop",
            prenom="Awa",
            email="awa.diop@example.com",
            telephone="+221771234567",
        )
        self.candidat2 = Candidature.objects.create(
            campagne=self.campagne,
            nom="Ba",
            prenom="Mamadou",
            email="mamadou.ba@example.com",
            telephone="+221779876543",
        )

        self.entretien = Entretien.objects.create(
            campagne=self.campagne,
            type=Entretien.Type.TECHNIQUE,
            statut=Entretien.Statut.PLANIFIE,
            date=date(2026, 9, 15),
            heure_debut=time(9, 0),
            heure_fin=time(12, 0),
            duree_minutes=45,
            lieu="Simplon Sénégal - Salle Dakar",
            lien_visio="https://meet.google.com/abc-defg-hij",
            notes="Évaluer la maîtrise des algorithmes et de Vue/Django.",
        )

    def test_echec_validation_aucun_jury(self):
        """Doit échouer si aucun jury n'est affecté à la session ni aux créneaux."""
        CreneauEntretien.objects.create(
            entretien=self.entretien,
            candidature=self.candidat1,
            heure_debut=time(9, 0),
            heure_fin=time(9, 45),
        )
        with self.assertRaises(ValidationError) as ctx:
            verifier_planification_entretien(self.entretien)
        self.assertIn("au moins un membre du jury", str(ctx.exception))

    def test_echec_validation_aucun_candidat_planifie(self):
        """Doit échouer si aucun candidat n'est assigné à un créneau."""
        self.entretien.jurys.add(self.jury1)
        CreneauEntretien.objects.create(
            entretien=self.entretien,
            candidature=None,
            heure_debut=time(9, 0),
            heure_fin=time(9, 45),
        )
        with self.assertRaises(ValidationError) as ctx:
            verifier_planification_entretien(self.entretien)
        self.assertIn("aucun candidat n'a été planifié", str(ctx.exception))

    def test_echec_validation_horaires_invalides(self):
        """Doit échouer si l'heure de fin est antérieure à l'heure de début."""
        self.entretien.jurys.add(self.jury1)
        CreneauEntretien.objects.create(
            entretien=self.entretien,
            candidature=self.candidat1,
            heure_debut=time(10, 0),
            heure_fin=time(9, 30),
        )
        with self.assertRaises(ValidationError) as ctx:
            verifier_planification_entretien(self.entretien)
        self.assertIn("antérieure à l'heure de fin", str(ctx.exception))

    def test_echec_validation_doublon_candidat(self):
        """Doit échouer si un candidat est assigné sur deux créneaux de la même session."""
        self.entretien.jurys.add(self.jury1)
        CreneauEntretien.objects.create(
            entretien=self.entretien,
            candidature=self.candidat1,
            heure_debut=time(9, 0),
            heure_fin=time(9, 45),
        )
        CreneauEntretien.objects.create(
            entretien=self.entretien,
            candidature=self.candidat1,
            heure_debut=time(10, 0),
            heure_fin=time(10, 45),
        )
        with self.assertRaises(ValidationError) as ctx:
            verifier_planification_entretien(self.entretien)
        self.assertIn("plusieurs créneaux", str(ctx.exception))

    def test_confirmation_reussie_avec_emails(self):
        """
        Scénario de succès complet :
        - 2 créneaux, 2 candidats, 2 jurys
        - Convocations créées et horodatées
        - Statut passé à CONFIRME
        - Emails envoyés (2 aux candidats + 2 plannings aux jurys)
        """
        self.entretien.jurys.add(self.jury1, self.jury2)

        cr1 = CreneauEntretien.objects.create(
            entretien=self.entretien,
            candidature=self.candidat1,
            heure_debut=time(9, 0),
            heure_fin=time(9, 45),
        )
        cr2 = CreneauEntretien.objects.create(
            entretien=self.entretien,
            candidature=self.candidat2,
            heure_debut=time(10, 0),
            heure_fin=time(10, 45),
        )

        mail.outbox.clear()

        result = confirmer_et_envoyer_convocations(self.entretien, envoyer_emails=True)

        self.assertTrue(result["success"])
        self.assertEqual(result["statut"], Entretien.Statut.CONFIRME)
        self.assertEqual(result["total_candidats"], 2)
        self.assertEqual(result["emails_candidats_envoyes"], 2)
        self.assertEqual(result["total_jurys"], 2)
        self.assertEqual(result["emails_jurys_envoyes"], 2)

        # Vérification en base de données
        self.entretien.refresh_from_db()
        self.assertEqual(self.entretien.statut, Entretien.Statut.CONFIRME)

        cr1.refresh_from_db()
        cr2.refresh_from_db()
        self.assertEqual(cr1.statut, CreneauEntretien.Statut.CONFIRME)
        self.assertEqual(cr2.statut, CreneauEntretien.Statut.CONFIRME)

        convs = ConvocationEntretien.objects.filter(entretien=self.entretien)
        self.assertEqual(convs.count(), 2)

        conv1 = convs.get(candidature=self.candidat1)
        self.assertEqual(conv1.statut, ConvocationEntretien.Statut.CONFIRME)
        self.assertEqual(conv1.heure_debut, time(9, 0))
        self.assertEqual(conv1.heure_fin, time(9, 45))
        self.assertEqual(conv1.lieu, self.entretien.lieu)
        self.assertEqual(conv1.lien_visio, self.entretien.lien_visio)
        self.assertIsNotNone(conv1.date_envoi)

        # Vérification des emails envoyés (2 candidats + 2 jurys = 4 emails au total)
        self.assertEqual(len(mail.outbox), 4)

        emails_recus = [m.to[0] for m in mail.outbox]
        self.assertIn("awa.diop@example.com", emails_recus)
        self.assertIn("mamadou.ba@example.com", emails_recus)
        self.assertIn("jury1@simplon.sn", emails_recus)
        self.assertIn("jury2@simplon.sn", emails_recus)


class EntretienAPITests(TestCase):
    """Tests d'intégration des endpoints de l'API REST."""

    def setUp(self):
        self.client = APIClient()

        self.admin = User.objects.create_user(
            email="admin@simplon.sn",
            first_name="Admin",
            last_name="User",
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
            is_staff=True,
        )

        self.jury = User.objects.create_user(
            email="jury.api@simplon.sn",
            first_name="Sophie",
            last_name="Martin",
            role=User.Role.JURY,
            status=User.Status.ACTIVE,
        )

        self.candidat_user = User.objects.create_user(
            email="candidat.connecte@example.com",
            first_name="Amadou",
            last_name="Diallo",
            role=User.Role.CANDIDAT,
            status=User.Status.ACTIVE,
        )

        self.referentiel = Referentiel.objects.create(
            title="Design Studio",
            description="Référentiel UI/UX"
        )
        self.campagne = Campagne.objects.create(
            title="Promotion UX/UI 2026",
            description="Campagne Design",
            begin_date=date(2026, 2, 1),
            end_date=date(2026, 11, 30),
            status=Campagne.Status.PUBLIEE,
            referentiel=self.referentiel,
        )

        self.candidature = Candidature.objects.create(
            campagne=self.campagne,
            nom="Diallo",
            prenom="Amadou",
            email="candidat.connecte@example.com",
            telephone="+221770001122",
        )

        self.entretien = Entretien.objects.create(
            campagne=self.campagne,
            type=Entretien.Type.MOTIVATION,
            statut=Entretien.Statut.PLANIFIE,
            date=date(2026, 9, 20),
            heure_debut=time(14, 0),
            heure_fin=time(16, 0),
            duree_minutes=45,
            lieu="En ligne (Google Meet)",
            lien_visio="https://meet.google.com/xyz-uvwx-rst",
            notes="Consignes motivationnelles",
        )
        self.entretien.jurys.add(self.jury)

        self.creneau = CreneauEntretien.objects.create(
            entretien=self.entretien,
            candidature=self.candidature,
            heure_debut=time(14, 0),
            heure_fin=time(14, 45),
        )

    def test_endpoint_confirmer_et_convoquer_succes(self):
        """L'admin appelle l'action 'confirmer-et-convoquer' avec succès."""
        self.client.force_authenticate(user=self.admin)
        url = f"/api/entretiens/{self.entretien.id}/confirmer-et-convoquer/"

        response = self.client.post(url, {"envoyer_emails": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["statut"], Entretien.Statut.CONFIRME)
        self.assertEqual(response.data["total_candidats"], 1)
        self.assertEqual(len(response.data["convocations"]), 1)

    def test_endpoint_confirmer_interdit_pour_candidat(self):
        """Un candidat ne peut pas déclencher la confirmation d'une session."""
        self.client.force_authenticate(user=self.candidat_user)
        url = f"/api/entretiens/{self.entretien.id}/confirmer-et-convoquer/"

        response = self.client.post(url, {"envoyer_emails": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_endpoint_planning_jurys(self):
        """Consultation du planning structuré par jury."""
        self.client.force_authenticate(user=self.admin)
        url = f"/api/entretiens/{self.entretien.id}/planning-jurys/"

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["campagne"], self.campagne.title)
        self.assertEqual(len(response.data["planning"]), 1)
        self.assertEqual(response.data["planning"][0]["jury"]["email"], self.jury.email)

    def test_espace_candidat_mes_convocations(self):
        """Le candidat connecté consulte ses propres convocations d'entretiens."""
        # Confirmer d'abord la session
        confirmer_et_envoyer_convocations(self.entretien, envoyer_emails=False)

        self.client.force_authenticate(user=self.candidat_user)
        url = "/api/candidat/entretiens/mes-convocations/"

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["candidature_details"]["email"], self.candidat_user.email)
        self.assertEqual(response.data[0]["statut"], "confirme")


class QuestionEntretienTests(TestCase):
    """Tests des questions d'entretien et des réponses des jurys."""

    def setUp(self):
        self.client = APIClient()
        self.referentiel = Referentiel.objects.create(
            title="Développement Web & IA",
            description="Référentiel compétences web & IA"
        )
        self.campagne = Campagne.objects.create(
            title="Promotion Dev Web IA 2026",
            description="Campagne de recrutement",
            begin_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=Campagne.Status.PUBLIEE,
            referentiel=self.referentiel,
        )

        self.admin = User.objects.create_user(
            email="admin.questions@simplon.sn",
            first_name="Admin",
            last_name="Questions",
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
            is_staff=True,
        )
        self.jury = User.objects.create_user(
            email="jury.questions@simplon.sn",
            first_name="Jury",
            last_name="Test",
            role=User.Role.JURY,
            status=User.Status.ACTIVE,
        )
        self.candidat = Candidature.objects.create(
            campagne=self.campagne,
            nom="Candidat",
            prenom="Test",
            email="candidat.questions@example.com",
            telephone="+221770001122",
        )

        self.entretien = Entretien.objects.create(
            campagne=self.campagne,
            type=Entretien.Type.TECHNIQUE,
            statut=Entretien.Statut.PLANIFIE,
            date=date(2026, 9, 15),
            heure_debut=time(9, 0),
            heure_fin=time(12, 0),
            duree_minutes=45,
            lieu="Simplon Sénégal",
            notes="Évaluer les compétences techniques.",
        )
        self.entretien.jurys.add(self.jury)

        self.creneau = CreneauEntretien.objects.create(
            entretien=self.entretien,
            candidature=self.candidat,
            heure_debut=time(9, 0),
            heure_fin=time(9, 45),
        )

        self.question = QuestionEntretien.objects.create(
            campagne=self.campagne,
            intitule="Quelle est votre expérience avec Django ?",
            type_question=QuestionEntretien.TypeQuestion.TEXTAREA,
            ordre=1,
            obligatoire=True,
            note_max=10,
        )

    def test_admin_cree_question(self):
        """L'administrateur peut créer une question."""
        self.client.force_authenticate(user=self.admin)
        url = "/api/questions-entretien/"
        payload = {
            "campagne": self.campagne.id,
            "intitule": "Question de test",
            "type_question": "TEXT",
            "ordre": 2,
            "obligatoire": False,
            "note_max": 5,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["intitule"], "Question de test")

    def test_candidat_ne_peut_pas_creer_question(self):
        """Un candidat ne peut pas créer de question."""
        candidat_user = User.objects.create_user(
            email="candidat.test@example.com",
            first_name="Candidat",
            last_name="User",
            role=User.Role.CANDIDAT,
            status=User.Status.ACTIVE,
        )
        self.client.force_authenticate(user=candidat_user)
        url = "/api/questions-entretien/"
        payload = {
            "campagne": self.campagne.id,
            "intitule": "Question interdite",
            "type_question": "TEXT",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_questions_associees_auto_confirmation(self):
        """Les questions de la campagne sont associées automatiquement à la confirmation."""
        confirmer_et_envoyer_convocations(self.entretien, envoyer_emails=False)
        self.entretien.refresh_from_db()
        self.assertTrue(self.entretien.questions_entretien.filter(id=self.question.id).exists())

    def test_jury_recupere_questions_entretien(self):
        """Le jury assigné récupère les questions de son entretien."""
        confirmer_et_envoyer_convocations(self.entretien, envoyer_emails=False)
        self.client.force_authenticate(user=self.jury)
        url = f"/api/entretiens/{self.entretien.id}/questions/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["questions"]), 1)
        self.assertEqual(response.data["questions"][0]["intitule"], self.question.intitule)
        self.assertEqual(response.data["score_total"], 0)

    def test_jury_saisit_reponse(self):
        """Le jury peut saisir une réponse, une note et un commentaire."""
        confirmer_et_envoyer_convocations(self.entretien, envoyer_emails=False)
        self.client.force_authenticate(user=self.jury)
        url = f"/api/entretiens/{self.entretien.id}/reponses/"
        payload = {
            "question": self.question.id,
            "reponse": "Le candidat a une bonne maîtrise de Django.",
            "note": 8,
            "commentaire": "Excellente connaissance des ORM.",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["score_total"], 8)

    def test_jury_ne_peut_pas_acceder_entretien_non_assigne(self):
        """Un jury non assigné ne peut pas accéder aux questions."""
        autre_jury = User.objects.create_user(
            email="autre.jury@simplon.sn",
            first_name="Autre",
            last_name="Jury",
            role=User.Role.JURY,
            status=User.Status.ACTIVE,
        )
        self.client.force_authenticate(user=autre_jury)
        url = f"/api/entretiens/{self.entretien.id}/questions/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_score_total_auto(self):
        """Le score total est calculé automatiquement à partir des réponses."""
        confirmer_et_envoyer_convocations(self.entretien, envoyer_emails=False)
        ReponseEntretien.objects.create(
            entretien=self.entretien,
            question=self.question,
            jury=self.jury,
            note=7,
        )
        self.assertEqual(self.entretien.score_total, 7)
