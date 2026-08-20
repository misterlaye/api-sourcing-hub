from unittest.mock import patch

from django.contrib.auth.tokens import default_token_generator
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User
from .tokens import generate_invitation_token


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
)
class AccountsAPITests(APITestCase):
    def setUp(self):
        # Create Admin
        self.admin_user = User.objects.create_superuser(
            email='admin@simplon.co',
            password='AdminPassword123!',
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
            is_profile_complete=True,
        )

        # Create Active Candidate
        self.candidate_user = User.objects.create_user(
            email='candidat@simplon.co',
            password='CandidatePassword123!',
            role=User.Role.CANDIDAT,
            status=User.Status.ACTIVE,
            is_profile_complete=False,
        )

    def test_login_success(self):
        url = reverse('accounts:login')
        response = self.client.post(url, {
            'email': 'admin@simplon.co',
            'password': 'AdminPassword123!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], 'admin@simplon.co')
        self.assertEqual(response.data['user']['role'], 'ADMIN')

    def test_login_fails_for_invited_user(self):
        User.objects.create_user(
            email='invited@simplon.co',
            role=User.Role.JURY,
            status=User.Status.INVITED
        )
        url = reverse('accounts:login')
        response = self.client.post(url, {
            'email': 'invited@simplon.co',
            'password': 'SomePassword123!'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('accounts.tasks.send_invitation_email_task.delay')
    def test_admin_invite_user(self, mock_email_task):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('accounts:user-list')
        response = self.client.post(url, {
            'email': 'new_member@simplon.co',
            'role': 'JURY'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='new_member@simplon.co', status=User.Status.INVITED).exists())

    def test_candidate_cannot_invite_user(self):
        self.client.force_authenticate(user=self.candidate_user)
        url = reverse('accounts:user-list')
        response = self.client.post(url, {
            'email': 'hacker@simplon.co',
            'role': 'ADMIN'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_account_activation(self):
        from django.utils import timezone
        invited = User.objects.create_user(
            email='to_activate@simplon.co',
            role=User.Role.CANDIDAT,
            status=User.Status.INVITED,
            last_invited_at=timezone.now()
        )
        token = generate_invitation_token(invited)

        url = reverse('accounts:account-activate')
        response = self.client.post(url, {
            'token': token,
            'password': 'NewSecurePassword123!',
            'password_confirm': 'NewSecurePassword123!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        invited.refresh_from_db()
        self.assertEqual(invited.status, User.Status.ACTIVE)
        self.assertTrue(invited.check_password('NewSecurePassword123!'))

    def test_logout_and_token_refresh(self):
        # 1. Login
        login_res = self.client.post(reverse('accounts:login'), {
            'email': 'admin@simplon.co',
            'password': 'AdminPassword123!'
        })
        access = login_res.data['access']
        refresh = login_res.data['refresh']

        # 2. Token refresh
        refresh_res = self.client.post(reverse('accounts:token_refresh'), {
            'refresh': refresh
        })
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_res.data)
        new_refresh = refresh_res.data.get('refresh', refresh)

        # 3. Logout
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        logout_res = self.client.post(reverse('accounts:logout'), {
            'refresh': new_refresh
        })
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

    @patch('accounts.tasks.send_password_reset_email_task.delay')
    def test_password_reset_flow(self, mock_reset_email):
        # 1. Request Reset
        req_res = self.client.post(reverse('accounts:password-reset-request'), {
            'email': 'candidat@simplon.co'
        })
        self.assertEqual(req_res.status_code, status.HTTP_202_ACCEPTED)

        # 2. Confirm Reset
        uid = urlsafe_base64_encode(force_bytes(self.candidate_user.pk))
        token = default_token_generator.make_token(self.candidate_user)

        confirm_url = reverse('accounts:password-reset-confirm', kwargs={'uid': uid, 'token': token})
        confirm_res = self.client.post(confirm_url, {
            'new_password': 'BrandNewPassword123!',
            'new_password_confirm': 'BrandNewPassword123!'
        })
        self.assertEqual(confirm_res.status_code, status.HTTP_200_OK)

        self.candidate_user.refresh_from_db()
        self.assertTrue(self.candidate_user.check_password('BrandNewPassword123!'))

    def test_get_and_update_me(self):
        self.client.force_authenticate(user=self.candidate_user)
        url = reverse('accounts:user-me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'candidat@simplon.co')

        # Patch me
        patch_res = self.client.patch(url, {
            'first_name': 'Bineta',
            'last_name': 'Badiane',
            'phone_number': '+221770000000',
        })
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.candidate_user.refresh_from_db()
        self.assertEqual(self.candidate_user.first_name, 'Bineta')
        self.assertEqual(self.candidate_user.last_name, 'Badiane')

    def test_admin_can_list_and_update_user(self):
        self.client.force_authenticate(user=self.admin_user)
        # List
        list_res = self.client.get(reverse('accounts:user-list'))
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)

        # Update
        detail_url = reverse('accounts:user-detail', kwargs={'pk': self.candidate_user.pk})
        update_res = self.client.patch(detail_url, {
            'first_name': 'UpdatedCandidate',
        })
        self.assertEqual(update_res.status_code, status.HTTP_200_OK)
        self.candidate_user.refresh_from_db()
        self.assertEqual(self.candidate_user.first_name, 'UpdatedCandidate')
