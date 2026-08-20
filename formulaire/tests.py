from datetime import date
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from campagne.models import Campagne, Referentiel
from candidature.models import Candidature
from formulaire.models import (
    Formulaire,
    SectionFormulaire,
    Question,
    OptionQuestion,
    ReponseQuestion,
    ReponseOption,
)

User = get_user_model()


class FormulaireAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin_form@test.com",
            password="AdminPassword123!",
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
            is_profile_complete=True,
        )
        self.candidate = User.objects.create_user(
            email="candidate_form@test.com",
            password="CandidatePassword123!",
            role=User.Role.CANDIDAT,
            status=User.Status.ACTIVE,
            is_profile_complete=True,
            first_name="Jane",
            last_name="Doe",
        )
        self.referentiel = Referentiel.objects.create(
            title="Referentiel Web",
            description="Formation dev web"
        )
        self.campagne = Campagne.objects.create(
            title="Promo 2026",
            description="Campagne 2026",
            begin_date=date(2026, 9, 1),
            end_date=date(2026, 12, 31),
            status=Campagne.Status.PUBLIEE,
            referentiel=self.referentiel,
        )

    def test_admin_can_create_full_formulaire_with_nested_sections(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("formulaire:formulaire-list")
        payload = {
            "titre": "Formulaire de candidature DWWM",
            "description": "Merci de remplir soigneusement",
            "campagne": self.campagne.id,
            "sections": [
                {
                    "titre": "État Civil",
                    "description": "Vos coordonnées",
                    "ordre": 0,
                    "questions": [
                        {
                            "texte": "Votre nom de famille",
                            "type_question": "TEXT",
                            "obligatoire": True,
                            "ordre": 0,
                            "options": []
                        },
                        {
                            "texte": "Votre genre",
                            "type_question": "RADIO",
                            "obligatoire": True,
                            "ordre": 1,
                            "options": [
                                {"texte": "Femme", "valeur": "femme", "ordre": 0},
                                {"texte": "Homme", "valeur": "homme", "ordre": 1}
                            ]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Formulaire.objects.count(), 1)
        self.assertEqual(SectionFormulaire.objects.count(), 1)
        self.assertEqual(Question.objects.count(), 2)
        self.assertEqual(OptionQuestion.objects.count(), 2)

    def test_candidate_cannot_create_formulaire(self):
        self.client.force_authenticate(user=self.candidate)
        url = reverse("formulaire:formulaire-list")
        response = self.client.post(url, {
            "titre": "Hacked Form",
            "campagne": self.campagne.id,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_publish_validation_requires_sections_questions_and_options(self):
        self.client.force_authenticate(user=self.admin)
        # Formulaire sans section
        form = Formulaire.objects.create(
            titre="Formulaire vide",
            campagne=self.campagne,
        )
        publier_url = reverse("formulaire:formulaire-publier", args=[form.pk])
        res = self.client.post(publier_url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("section", res.data["detail"])

        # Ajouter section avec question RADIO sans assez d'options
        sec = SectionFormulaire.objects.create(formulaire=form, titre="Sec 1", ordre=0)
        q = Question.objects.create(
            section=sec,
            texte="Choix unique",
            type_question=Question.TypeQuestion.RADIO,
            obligatoire=True,
            ordre=0
        )
        # 0 options
        res2 = self.client.post(publier_url)
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

        # 1 option (il en faut au moins 2)
        OptionQuestion.objects.create(question=q, texte="Opt 1", valeur="1", ordre=0)
        res3 = self.client.post(publier_url)
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)

        # 2 options -> succès
        OptionQuestion.objects.create(question=q, texte="Opt 2", valeur="2", ordre=1)
        res4 = self.client.post(publier_url)
        self.assertEqual(res4.status_code, status.HTTP_200_OK)
        form.refresh_from_db()
        self.assertTrue(form.publier)
        self.assertTrue(form.actif)

    def test_preview_formulaire(self):
        form = Formulaire.objects.create(titre="Form Preview", campagne=self.campagne)
        sec = SectionFormulaire.objects.create(formulaire=form, titre="Sec Preview", ordre=0)
        Question.objects.create(
            section=sec,
            texte="Question text",
            type_question=Question.TypeQuestion.TEXT,
            obligatoire=False,
            ordre=0
        )
        self.client.force_authenticate(user=self.admin)
        preview_url = reverse("formulaire:formulaire-preview", args=[form.pk])
        response = self.client.get(preview_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["titre"], "Form Preview")
        self.assertEqual(len(response.data["sections"]), 1)

    def test_submission_and_mes_reponses_flow(self):
        # 1. Configurer un formulaire publié
        form = Formulaire.objects.create(
            titre="Candidature Promo",
            campagne=self.campagne,
            publier=True,
            actif=True
        )
        sec = SectionFormulaire.objects.create(formulaire=form, titre="Section 1", ordre=0)
        q_text = Question.objects.create(
            section=sec,
            texte="Pourquoi postulez-vous ?",
            type_question=Question.TypeQuestion.TEXT,
            obligatoire=True,
            ordre=0
        )
        q_radio = Question.objects.create(
            section=sec,
            texte="Avez-vous un ordinateur portable ?",
            type_question=Question.TypeQuestion.RADIO,
            obligatoire=True,
            ordre=1
        )
        opt_oui = OptionQuestion.objects.create(question=q_radio, texte="Oui", valeur="oui", ordre=0)
        opt_non = OptionQuestion.objects.create(question=q_radio, texte="Non", valeur="non", ordre=1)

        q_check = Question.objects.create(
            section=sec,
            texte="Langages connus",
            type_question=Question.TypeQuestion.CHECKBOX,
            obligatoire=False,
            ordre=2
        )
        opt_py = OptionQuestion.objects.create(question=q_check, texte="Python", valeur="python", ordre=0)
        opt_js = OptionQuestion.objects.create(question=q_check, texte="JavaScript", valeur="javascript", ordre=1)

        # 2. Soumission par la candidate
        self.client.force_authenticate(user=self.candidate)
        soumettre_url = reverse("formulaire:formulaire-soumettre", args=[form.pk])
        payload = {
            "reponses": [
                {
                    "question": q_text.id,
                    "valeur": "Passionnée par le développement"
                },
                {
                    "question": q_radio.id,
                    "options": [opt_oui.id]
                },
                {
                    "question": q_check.id,
                    "options": [opt_py.id, opt_js.id]
                }
            ]
        }
        res_sub = self.client.post(soumettre_url, payload, format="json")
        self.assertEqual(res_sub.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ReponseQuestion.objects.count(), 3)
        self.assertEqual(ReponseOption.objects.count(), 3)

        # 3. Consultation de mes réponses
        mes_reponses_url = reverse("formulaire:formulaire-mes-reponses", args=[form.pk])
        res_get = self.client.get(mes_reponses_url)
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_get.data["reponses"]), 3)

        # 4. Consultation des réponses côté Admin
        cand = Candidature.objects.get(email=self.candidate.email, campagne=self.campagne)
        self.client.force_authenticate(user=self.admin)
        admin_rep_url = reverse("formulaire:candidature-reponses", args=[cand.pk])
        res_admin = self.client.get(admin_rep_url)
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        self.assertEqual(res_admin.data["candidature"], cand.pk)
        self.assertEqual(len(res_admin.data["reponses"]), 3)

    def test_anonymous_user_can_view_published_formulaire(self):
        # 1. Publié -> accessible au public
        form = Formulaire.objects.create(
            titre="Formulaire Public",
            campagne=self.campagne,
            publier=True,
            actif=True
        )
        url = reverse("formulaire:formulaire-detail", args=[form.pk])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["titre"], "Formulaire Public")

        # 2. Action dédiée public
        public_url = reverse("formulaire:formulaire-public", args=[form.pk])
        res_pub = self.client.get(public_url)
        self.assertEqual(res_pub.status_code, status.HTTP_200_OK)

    def test_anonymous_user_cannot_view_draft_formulaire(self):
        # Brouillon -> refusé pour un utilisateur anonyme
        form_draft = Formulaire.objects.create(
            titre="Formulaire Brouillon",
            campagne=self.campagne,
            publier=False,
            actif=True
        )
        url = reverse("formulaire:formulaire-detail", args=[form_draft.pk])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_user_submits_formulaire_and_creates_en_attente_candidature(self):
        # Un candidat anonyme (sans compte ni JWT) soumet sa candidature
        form = Formulaire.objects.create(
            titre="Formulaire Candidature Public",
            campagne=self.campagne,
            publier=True,
            actif=True
        )
        sec = SectionFormulaire.objects.create(formulaire=form, titre="Infos", ordre=0)
        q = Question.objects.create(
            section=sec,
            texte="Motivation",
            type_question=Question.TypeQuestion.TEXT,
            obligatoire=True,
            ordre=0
        )

        soumettre_url = reverse("formulaire:formulaire-soumettre", args=[form.pk])
        payload = {
            "nom": "Ndiaye",
            "prenom": "Ousmane",
            "email": "ousmane.ndiaye@example.com",
            "telephone": "+221771112233",
            "reponses": [
                {
                    "question": q.id,
                    "valeur": "Très motivé pour la formation"
                }
            ]
        }
        res = self.client.post(soumettre_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Vérification qu'une Candidature a été créée avec statut EN_ATTENTE
        cand = Candidature.objects.get(email="ousmane.ndiaye@example.com", campagne=self.campagne)
        self.assertEqual(cand.nom, "Ndiaye")
        self.assertEqual(cand.prenom, "Ousmane")
        self.assertEqual(cand.telephone, "+221771112233")
        self.assertEqual(cand.status, Candidature.Status.EN_ATTENTE)

        # Vérification qu'AUCUN compte utilisateur n'a été créé
        self.assertFalse(User.objects.filter(email="ousmane.ndiaye@example.com").exists())

    def test_anonymous_user_cannot_create_or_publish_formulaire(self):
        # Tentative de création anonyme
        url_create = reverse("formulaire:formulaire-list")
        res = self.client.post(url_create, {"titre": "Hacked"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # Tentative de publication anonyme
        form = Formulaire.objects.create(titre="Draft", campagne=self.campagne)
        url_pub = reverse("formulaire:formulaire-publier", args=[form.pk])
        res_pub = self.client.post(url_pub)
        self.assertEqual(res_pub.status_code, status.HTTP_401_UNAUTHORIZED)
