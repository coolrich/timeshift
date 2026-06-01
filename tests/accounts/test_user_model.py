import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:

    def test_create_user(self):
        user = User.objects.create_user(
            username="John",
            password="123SuperSecret!",
            email="john@example.com",
            phone_number="+380969817231"
        )

        assert User.objects.count() == 1
        assert User.objects.filter(username="John").exists()
        assert user.check_password("123SuperSecret!")

    def test_create_user_with_fullname(self):
        User.objects.create_user(
            username="John",
            full_name="John Doe",
            password="123SuperSecret!",
            email="john@example.com",
            phone_number="+380969817231"
        )

        assert User.objects.filter(full_name="John Doe").exists()