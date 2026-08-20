from datetime import date, time
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from campagne.models import Campagne, Referentiel, ReunionInformation, CreneauRI
from candidature.models import Candidature, ConvocationRI

User = get_user_model()


class CandidatureAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="Password123!",
            role=User.Role.ADMIN,
        )
        self.referentiel = Referentiel.objects.create(
            title="Referentiel Test",
            description="Description test"
        )
        self.campagne = Campagne.objects.create(
            title="Campagne Test Développeur Web",
            description="Desc",
            begin_date=date(2026, 9, 1),
            end_date=date(2026, 12, 31),
            status=Campagne.Status.PUBLIEE,
            referentiel=self.referentiel,
        )
        self.reunion = ReunionInformation.objects.create(
            campagne=self.campagne,
            titre="Réunion d'Information - DW 2026",
            date=date(2026, 8, 25),
            lieu="Simplon Dakar",
            description="Session d'orientation",
        )
        self.creneau_matin = CreneauRI.objects.create(
            reunion=self.reunion,
            nom="Groupe matin",
            heure_debut=time(9, 0),
            heure_fin=time(12, 0),
            capacite=30,
        )
        self.creneau_soir = CreneauRI.objects.create(
            reunion=self.reunion,
            nom="Groupe soir",
            heure_debut=time(14, 0),
            heure_fin=time(17, 0),
            capacite=30,
        )
        self.candidat1 = Candidature.objects.create(
            campagne=self.campagne,
            nom="Diarra",
            prenom="Fatou",
            email="fatou.diarra@example.com",
            telephone="+221770000001",
        )
        self.candidat2 = Candidature.objects.create(
            campagne=self.campagne,
            nom="Sow",
            prenom="Mamadou",
            email="mamadou.sow@example.com",
            telephone="+221770000002",
        )

    def test_public_create_candidature_links_campagne_correctly(self):
        url = reverse("candidature:candidature-create-list")
        payload = {
            "campagne": self.campagne.id,
            "nom": "Ndiaye",
            "prenom": "Ousmane",
            "email": "ousmane.ndiaye@example.com",
            "telephone": "+221771234567",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Candidature.objects.count(), 3)

        cand = Candidature.objects.get(email="ousmane.ndiaye@example.com")
        self.assertEqual(cand.campagne, self.campagne)
        self.assertEqual(cand.status, Candidature.Status.EN_ATTENTE)

    def test_campagne_candidats_endpoint(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:campagne-candidats", kwargs={"pk": self.campagne.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn("convocation_ri", response.data[0])

    def test_batch_create_convocations_ri(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:reunion-convocations", kwargs={"pk": self.reunion.id})
        payload = {
            "candidature_ids": [self.candidat1.id, self.candidat2.id],
            "creneau_id": self.creneau_matin.id,
            "envoyer_email": False,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 2)
        self.assertEqual(ConvocationRI.objects.count(), 2)

        conv1 = ConvocationRI.objects.get(candidature=self.candidat1)
        self.assertEqual(conv1.creneau, self.creneau_matin)
        self.assertEqual(conv1.statut, ConvocationRI.StatutPresence.ABSENT)
        self.assertIsNotNone(conv1.token)

    def test_scan_presence_flow_and_anti_duplicate(self):
        self.client.force_authenticate(user=self.admin)
        conv1 = ConvocationRI.objects.create(
            candidature=self.candidat1,
            reunion_information=self.reunion,
            creneau=self.creneau_matin,
            statut=ConvocationRI.StatutPresence.ABSENT,
        )

        url = reverse("campagne:reunion-presence", kwargs={"pk": self.reunion.id})
        
        # 1. Premier scan : statut passe de ABSENT à PRESENT
        scan_payload = {"token": str(conv1.token)}
        response1 = self.client.post(url, scan_payload, format="json")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertTrue(response1.data["success"])
        self.assertFalse(response1.data["already_present"])
        self.assertEqual(response1.data["candidate"]["nom"], "Diarra")
        self.assertEqual(response1.data["creneau"]["nom"], "Groupe matin")

        conv1.refresh_from_db()
        self.assertEqual(conv1.statut, ConvocationRI.StatutPresence.PRESENT)
        self.assertIsNotNone(conv1.date_presence)

        self.candidat1.refresh_from_db()
        self.assertEqual(self.candidat1.status, Candidature.Status.PRESENT)

        # 2. Deuxième scan : même token -> already_present=True
        response2 = self.client.post(url, scan_payload, format="json")
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertTrue(response2.data["success"])
        self.assertTrue(response2.data["already_present"])
        self.assertIn("déjà", response2.data["message"])

    def test_scan_presence_with_invalid_token(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:reunion-presence", kwargs={"pk": self.reunion.id})
        response = self.client.post(url, {"token": "00000000-0000-0000-0000-000000000000"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["success"])
        self.assertIn("invalide", response.data["message"])

    def test_reunion_stats_endpoint(self):
        self.client.force_authenticate(user=self.admin)
        ConvocationRI.objects.create(
            candidature=self.candidat1,
            reunion_information=self.reunion,
            creneau=self.creneau_matin,
            statut=ConvocationRI.StatutPresence.PRESENT,
        )
        ConvocationRI.objects.create(
            candidature=self.candidat2,
            reunion_information=self.reunion,
            creneau=self.creneau_soir,
            statut=ConvocationRI.StatutPresence.ABSENT,
        )

        url = reverse("campagne:reunion-stats", kwargs={"pk": self.reunion.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 2)
        self.assertEqual(response.data["present"], 1)
        self.assertEqual(response.data["absent"], 1)
        self.assertEqual(len(response.data["creneaux"]), 2)

    def test_public_convocation_view_without_login(self):
        conv = ConvocationRI.objects.create(
            candidature=self.candidat1,
            reunion_information=self.reunion,
            creneau=self.creneau_matin,
        )
        url = f"/api/convocations-ri/public/{conv.token}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["candidature_nom"], "Diarra")
        self.assertIn("qr_code_base64", response.data)

