import uuid
from logging import getLogger

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

from accounts.models import UserSubscription
from tests.factories.plan import PlanFactory
from tests.factories.throttle import ThrottleFactory
from tests.factories.user import UserFactory

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
