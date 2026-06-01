import pprint
from logging import getLogger

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from tests.conftest import free_plan
from tests.utils.utils import get_current_method_path

logger = getLogger(__name__)
User = get_user_model()

@pytest.mark.django_db
class TestAccounts:

    @pytest.fixture(autouse=True)
    def setup(self, client):
        self.client = client

    def test_log_in_out(self):
        user = User.objects.create_user(username='testuser564',
                                 password='ohi;er;knb$&^*',
                                 email='testuser@example.com',
                                 phone_number='+380969817231')

        response = self.client.post(reverse("login"),
                                    {'username': 'testuser564',
                                     'password': 'ohi;er;knb$&^*'
                                     },
                                    follow=True
                                    )
        assert response.status_code == 200
        assert self.client.session.get('_auth_user_id') == str(user.id)
        assert self.client.session.get('_auth_user_backend') == 'django.contrib.auth.backends.ModelBackend'

        assert not self.client.logout()
        logger.debug(f"{get_current_method_path(self,self.test_log_in_out)}: "
                     f"auth_user_id: {self.client.session.get('_auth_user_id')}")
        assert self.client.session.get('_auth_user_id') is None


@pytest.mark.django_db
class TestUsers:

    @pytest.fixture(autouse=True)
    def setup(self, client, free_plan):
        self.client = client

    def test_create_user_success(self):
        username = 'john'
        response = self.client.post(
            reverse("signup"),
            {
                'username': username,
                'password1': 'SuperSecret123!',
                'password2': 'SuperSecret123!',
                'email': 'testuser@example.com',
                'phone_number': '+380969817231'
            },
            follow=True
        )
        logger.debug(f"{get_current_method_path(self,self.test_create_user_success)}: response: {pprint.pformat(response.text)}")
        assert response.status_code == 200
        assert f"Hi, {username}" in response.text
        user = User.objects.filter(username=username)
        assert user.exists()
        assert self.client.session.get('_auth_user_id') == str(user.first().id)

    def test_create_user_with_bad_password(self):
        username = 'John'
        response = self.client.post(
            reverse("signup"),
            {
                "username": username,
                "password1": "123",
                "password2": "123"
            }
        )
        logger.debug(f"TestUsers.test_create_user_with_bad_password(): response: {pprint.pformat(response.text)}")

        assert response.status_code == 200
        assert f"Hi, {username}" not in response.text
        assert self.client.session.get('_auth_user_id') is None
        assert not User.objects.filter(username=username).exists()
