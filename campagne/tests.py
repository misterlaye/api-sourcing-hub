from datetime import date, time

from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from .models import Referentiel, CritereSelection, Campagne, ReunionInformation, CreneauRI
from candidature.models import Candidature


User = get_user_model()


class CampagneRITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="adminpass",
            is_staff=True,
            is_active=True,
            role=User.Role.ADMIN,
        )
        self.user = User.objects.create_user(
            email="user@test.com",
            password="userpass",
            is_active=True,
            role=User.Role.CANDIDAT,
        )
        self.referentiel = Referentiel.objects.create(
            title="Dev", description="Développement"
        )
        self.critere = CritereSelection.objects.create(
            name="BAC+2", description="Niveau BAC+2"
        )
        self.campagne = Campagne.objects.create(
            title="Campagne Test",
            description="Desc",
            begin_date=date(2026, 9, 10),
            end_date=date(2026, 12, 31),
            status=Campagne.Status.BROUILLON,
            referentiel=self.referentiel,
        )
        self.campagne.criteres.add(self.critere)

    # ---------------------------------------------------------------
    # RI via /api/campagnes/{id}/reunion-information/
    # ---------------------------------------------------------------
    def test_admin_can_create_ri(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:campagne-reunion-information", args=[self.campagne.pk])
        payload = {
            "titre": "Réunion d'information",
            "date": "2026-09-10",
            "lieu": "Dakar",
            "description": "Présentation",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ReunionInformation.objects.count(), 1)
        self.assertEqual(response.data["titre"], "Réunion d'information")
        self.assertEqual(response.data["campagne"], self.campagne.pk)

    def test_second_ri_is_rejected(self):
        ReunionInformation.objects.create(
            campagne=self.campagne,
            titre="RI 1",
            date=date(2026, 9, 10),
            lieu="Dakar",
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:campagne-reunion-information", args=[self.campagne.pk])
        payload = {
            "titre": "RI 2",
            "date": "2026-09-11",
            "lieu": "Dakar",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_user_cannot_create_ri(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("campagne:campagne-reunion-information", args=[self.campagne.pk])
        payload = {
            "titre": "Réunion d'information",
            "date": "2026-09-10",
            "lieu": "Dakar",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_can_read_ri(self):
        ri = ReunionInformation.objects.create(
            campagne=self.campagne,
            titre="Réunion d'information",
            date=date(2026, 9, 10),
            lieu="Dakar",
        )
        self.client.force_authenticate(user=self.user)
        url = reverse("campagne:campagne-reunion-information", args=[self.campagne.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], ri.pk)
        self.assertEqual(response.data["titre"], "Réunion d'information")
        self.assertEqual(response.data["campagne"], self.campagne.pk)

    def test_admin_can_patch_ri(self):
        ri = ReunionInformation.objects.create(
            campagne=self.campagne,
            titre="Ancien titre",
            date=date(2026, 9, 10),
            lieu="Dakar",
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:campagne-reunion-information", args=[self.campagne.pk])
        payload = {"titre": "Nouveau titre"}
        response = self.client.patch(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ri.refresh_from_db()
        self.assertEqual(ri.titre, "Nouveau titre")

    def test_admin_can_delete_ri(self):
        ReunionInformation.objects.create(
            campagne=self.campagne,
            titre="RI à supprimer",
            date=date(2026, 9, 10),
            lieu="Dakar",
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:campagne-reunion-information", args=[self.campagne.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ReunionInformation.objects.count(), 0)

    def test_get_ri_returns_404_when_none(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:campagne-reunion-information", args=[self.campagne.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---------------------------------------------------------------
    # Créneaux via /api/reunions/{id}/creneaux/
    # ---------------------------------------------------------------
    def test_admin_can_create_creneau(self):
        ri = ReunionInformation.objects.create(
            campagne=self.campagne,
            titre="Réunion",
            date=date(2026, 9, 10),
            lieu="Dakar",
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:reunion-creneaux", args=[ri.pk])
        payload = {"heure_debut": "10:00:00", "heure_fin": "13:00:00", "capacite": 30}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CreneauRI.objects.count(), 1)
        self.assertEqual(response.data["heure_debut"], "10:00:00")
        self.assertEqual(response.data["capacite"], 30)

    def test_user_can_list_creneaux(self):
        ri = ReunionInformation.objects.create(
            campagne=self.campagne,
            titre="Réunion",
            date=date(2026, 9, 10),
            lieu="Dakar",
        )
        CreneauRI.objects.create(
            reunion=ri, heure_debut=time(10, 0), heure_fin=time(13, 0), capacite=30
        )
        CreneauRI.objects.create(
            reunion=ri, heure_debut=time(15, 0), heure_fin=time(18, 0), capacite=30
        )
        self.client.force_authenticate(user=self.user)
        url = reverse("campagne:reunion-creneaux", args=[ri.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_creneau_heure_fin_must_be_superieure(self):
        ri = ReunionInformation.objects.create(
            campagne=self.campagne,
            titre="Réunion",
            date=date(2026, 9, 10),
            lieu="Dakar",
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:reunion-creneaux", args=[ri.pk])
        payload = {"heure_debut": "10:00:00", "heure_fin": "09:00:00", "capacite": 30}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("heure_fin", response.data)

    def test_creneau_capacite_must_be_positive(self):
        ri = ReunionInformation.objects.create(
            campagne=self.campagne,
            titre="Réunion",
            date=date(2026, 9, 10),
            lieu="Dakar",
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:reunion-creneaux", args=[ri.pk])
        payload = {"heure_debut": "10:00:00", "heure_fin": "13:00:00", "capacite": 0}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("capacite", response.data)

    def test_creneau_overlap_is_rejected(self):
        ri = ReunionInformation.objects.create(
            campagne=self.campagne,
            titre="Réunion",
            date=date(2026, 9, 10),
            lieu="Dakar",
        )
        CreneauRI.objects.create(
            reunion=ri, heure_debut=time(10, 0), heure_fin=time(13, 0), capacite=30
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:reunion-creneaux", args=[ri.pk])
        payload = {"heure_debut": "12:00:00", "heure_fin": "15:00:00", "capacite": 30}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_patch_creneau_via_reunion(self):
        ri = ReunionInformation.objects.create(
            campagne=self.campagne,
            titre="Réunion",
            date=date(2026, 9, 10),
            lieu="Dakar",
        )
        creneau = CreneauRI.objects.create(
            reunion=ri, heure_debut=time(10, 0), heure_fin=time(13, 0), capacite=30
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:creneau-ri-detail", args=[creneau.pk])
        payload = {"capacite": 50}
        response = self.client.patch(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        creneau.refresh_from_db()
        self.assertEqual(creneau.capacite, 50)

    def test_admin_can_delete_creneau_via_reunion(self):
        ri = ReunionInformation.objects.create(
            campagne=self.campagne,
            titre="Réunion",
            date=date(2026, 9, 10),
            lieu="Dakar",
        )
        creneau = CreneauRI.objects.create(
            reunion=ri, heure_debut=time(10, 0), heure_fin=time(13, 0), capacite=30
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:creneau-ri-detail", args=[creneau.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CreneauRI.objects.count(), 0)

    # ---------------------------------------------------------------
    # Règles métier supplémentaires
    # ---------------------------------------------------------------
    def test_ri_date_can_be_any_value(self):
        """La date de la RI n'est pas restreinte au futur pour les brouillons."""
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:campagne-reunion-information", args=[self.campagne.pk])
        payload = {
            "titre": "Réunion",
            "date": "2020-01-01",
            "lieu": "Dakar",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_campagne_publier_and_cloturer_workflow(self):
        self.client.force_authenticate(user=self.admin)
        # 1. Publier
        publier_url = reverse("campagne:campagne-publier", args=[self.campagne.pk])
        res_pub = self.client.post(publier_url)
        self.assertEqual(res_pub.status_code, status.HTTP_200_OK)
        self.campagne.refresh_from_db()
        self.assertEqual(self.campagne.status, Campagne.Status.PUBLIEE)

        # 2. Clôturer
        cloturer_url = reverse("campagne:campagne-cloturer", args=[self.campagne.pk])
        res_clot = self.client.post(cloturer_url)
        self.assertEqual(res_clot.status_code, status.HTTP_200_OK)
        self.campagne.refresh_from_db()
        self.assertEqual(self.campagne.status, Campagne.Status.CLOTUREE)

    def test_update_campagne_keeps_existing_past_begin_date(self):
        # Create a past campaign
        past_campagne = Campagne.objects.create(
            title="Old Campagne",
            description="Old Desc",
            begin_date=date(2020, 1, 1),
            end_date=date(2020, 6, 1),
            status=Campagne.Status.BROUILLON,
            referentiel=self.referentiel,
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:campagne-detail", args=[past_campagne.pk])
        response = self.client.patch(url, {"description": "Updated Old Desc"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        past_campagne.refresh_from_db()
        self.assertEqual(past_campagne.description, "Updated Old Desc")

    def test_campagne_nombre_candidatures_compte_reellement_les_candidatures(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("campagne:campagne-detail", args=[self.campagne.pk])

        # Initialement 0 candidatures
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["nombre_candidatures"], 0)

        # Ajout d'une 1ere candidature
        Candidature.objects.create(
            campagne=self.campagne,
            nom="Diop",
            prenom="Fatou",
            email="fatou.diop@example.com",
            telephone="+221770000001",
        )
        response = self.client.get(url)
        self.assertEqual(response.data["nombre_candidatures"], 1)

        # Ajout d'une 2eme candidature
        Candidature.objects.create(
            campagne=self.campagne,
            nom="Sow",
            prenom="Moussa",
            email="moussa.sow@example.com",
            telephone="+221770000002",
        )
        response = self.client.get(url)
        self.assertEqual(response.data["nombre_candidatures"], 2)

    def test_campagne_nombre_candidatures_isole_par_campagne(self):
        self.client.force_authenticate(user=self.admin)
        autre_campagne = Campagne.objects.create(
            title="Autre Campagne",
            description="Desc",
            begin_date=date(2026, 10, 1),
            end_date=date(2026, 11, 1),
            status=Campagne.Status.BROUILLON,
            referentiel=self.referentiel,
        )

        Candidature.objects.create(
            campagne=self.campagne,
            nom="Fall",
            prenom="Awa",
            email="awa.fall@example.com",
        )

        list_url = reverse("campagne:campagne-list")
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data_by_id = {item["id"]: item for item in response.data}
        self.assertEqual(data_by_id[self.campagne.pk]["nombre_candidatures"], 1)
        self.assertEqual(data_by_id[autre_campagne.pk]["nombre_candidatures"], 0)

