import uuid
from logging import getLogger

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db.models.fields.tuple_lookups import Tuple
from django.http import HttpRequest, QueryDict
from django.urls import reverse

from accounts.models import UserSubscription
from core.models import VirtualClock
from tests.factories.plan import PlanFactory
from tests.factories.throttle import ThrottleFactory
from tests.factories.user import UserFactory
from django.core.cache import cache

logger = getLogger(__name__)

User = get_user_model()

USER_TEST_PASSWORD = "testpass"


@pytest.fixture
def free_plan(db):
    logger.debug("Creating free plan")
    plan = PlanFactory.free()
    ThrottleFactory.clocks_create_scope(plan)
    ThrottleFactory.global_scope(plan)
    return plan


@pytest.fixture
def free_plan_conf(db):
    def conf(max_requests, period):
        logger.debug("Creating free plan")
        plan = PlanFactory.free()
        ThrottleFactory.clocks_create_scope(plan, max_requests, period)
        ThrottleFactory.global_scope(plan, max_requests, period)
        ThrottleFactory.token_refresh_scope(plan, max_requests, period)
        return plan

    return conf


@pytest.fixture
def pro_plan(db):
    logger.debug("Creating pro plan")
    plan = PlanFactory.pro()
    ThrottleFactory.clocks_create_scope(plan,
                                        max_requests=50,
                                        )
    ThrottleFactory.global_scope(plan,
                                 max_requests=1000
                                 )
    return plan


@pytest.fixture
def user(db, free_plan):
    logger.debug("Creating user")
    return UserFactory.with_plan(free_plan, password=USER_TEST_PASSWORD)


@pytest.fixture
def user_conf(db, free_plan_conf):
    def conf(max_requests, period):
        logger.debug("Creating user")
        return UserFactory.with_plan(free_plan_conf(max_requests, period), password=USER_TEST_PASSWORD)

    return conf


@pytest.fixture
def auth_client(client, user):
    logger.debug(f"tests.accounts.test_accounts_views.auth_client():"
                 f"username={user.username} password={USER_TEST_PASSWORD}")
    logged_in = client.login(username=user.username, password=USER_TEST_PASSWORD)
    logger.debug(f"tests.accounts.test_accounts_views.auth_client():"
                 f"logged_in:{logged_in}")
    assert logged_in, "Login failed!"
    return client


@pytest.fixture
def auth_client_conf(client, user_conf, clean_cache):
    """
    Returns:
        conf(max_requests:int, period:str):
            Returns:
                Tuple[User, Client]
    """
    def conf(max_requests:int, period:str):
        """
        Returns:
            Tuple[User, Client]
        """
        user = user_conf(max_requests, period)
        logger.debug(f"tests.accounts.test_accounts_views.auth_client():"
                     f"username={user.username} password={USER_TEST_PASSWORD}")
        logged_in = client.login(username=user.username, password=USER_TEST_PASSWORD)
        logger.debug(f"tests.accounts.test_accounts_views.auth_client():"
                     f"logged_in:{logged_in}")
        assert logged_in, "Login failed!"
        return user, client

    return conf


@pytest.fixture
async def users_async(db, free_plan):
    async def make_user(username, email, phone, max_clocks):
        new_user = await sync_to_async(User.objects.create_user)(
            username=f"{username}_{uuid.uuid4().hex[:6]}",
            password=USER_TEST_PASSWORD,
            email=email,
            phone_number=phone,
            max_clocks_count=max_clocks
        )

        await UserSubscription.objects.aget_or_create(
            user=new_user,
            plan=free_plan
        )
        logger.debug(f"{new_user.username} plan: {new_user.subscription.plan.name}")
        return new_user

    user = await make_user(
        "emily",
        "emily@example.com",
        "+380969817231",
        8
    )

    stranger = await make_user(
        "stranger",
        "stranger@example.com",
        "+380969817210",
        10
    )

    return user, stranger


@pytest.fixture
def users_factory_async(transactional_db):
    async def create(users_count, max_clocks_count, plan):
        users = []
        for i in range(users_count):
            user = await sync_to_async(User.objects.create_user)(
                # username=f"user_{i}",
                username=f"user_{i}_{uuid.uuid4().hex[:6]}",
                password="testpass",
                email=f"user_{i}@example.com",
                phone_number=f"+380{960000000 + i:09d}",
                max_clocks_count=max_clocks_count
            )
            # logger.debug(f"{user.username} max_clocks_count: {user.max_clocks_count}")
            await UserSubscription.objects.aget_or_create(
                user=user,
                plan=plan
            )

            users.append(user)
        return users

    return create


@pytest.fixture
def users_factory_sync(db, free_plan):
    def create(users_count, max_clocks_count):
        users = []
        for i in range(users_count):
            user = User.objects.create_user(
                # username=f"user_{i}",
                username=f"user_{i}_{uuid.uuid4().hex[:6]}",
                password=USER_TEST_PASSWORD,
                email=f"user_{i}@example.com",
                phone_number=f"+380{str(969817240 + i)[:9]}",
                max_clocks_count=max_clocks_count
            )
            # logger.debug(f"{user.username} max_clocks_count: {user.max_clocks_count}")
            UserSubscription.objects.get_or_create(
                user=user,
                plan=free_plan
            )

            users.append(user)
        return users

    return create


@pytest.fixture
def users_factory_bulk_sync(db, free_plan):
    def create(users_count, max_clocks_count):
        users = []

        for i in range(users_count):
            users.append(User(
                username=f"user_{i}_{uuid.uuid4().hex[:6]}",
                email=f"user_{i}@example.com",
                phone_number=f"+380{969817240 + i:09d}",
                max_clocks_count=max_clocks_count,
                password=make_password("testpass")  # ✔ правильно
            ))

        users = User.objects.bulk_create(users)

        UserSubscription.objects.bulk_create([
            UserSubscription(user=user, plan=free_plan)
            for user in users
        ])

        return users

    return create


@pytest.fixture
def users_factory_bulk_async(transactional_db, free_plan):
    async def create(users_count, max_clocks_count):
        def _create():
            users = []

            for i in range(users_count):
                users.append(User(
                    username=f"user_{i}_{uuid.uuid4().hex[:6]}",
                    email=f"user_{i}@example.com",
                    phone_number=f"+380{969817240 + i:09d}",
                    max_clocks_count=max_clocks_count,
                    password=make_password("testpass")
                ))

            users_created = User.objects.bulk_create(users)

            UserSubscription.objects.bulk_create([
                UserSubscription(user=user, plan=free_plan)
                for user in users_created
            ])

            return users_created

        return await sync_to_async(_create)()

    return create


@pytest.fixture
def owned_clock(user):
    return VirtualClock.objects.create(user_owner=user)


@pytest.fixture
def clock_control_url():
    def build(clock):
        return reverse("clock_control", args=[clock.id])

    return build


@pytest.fixture
def signup_data():
    return {
        "username": "newuser",
        "password1": "StrongPass123!",
        "password2": "StrongPass123!",
        "email": "newuser@example.com",
        "phone_number": "+380687807356",
    }


@pytest.fixture
def post_request():
    request = HttpRequest()
    request.method = "POST"
    request.POST = QueryDict("test=true")
    return request


@pytest.fixture
def clean_cache():
    cache.clear()
    yield
    cache.clear()
