# accounts/factories/plan.py

from accounts.models import Plan


class PlanFactory:
    @staticmethod
    def create(**kwargs):
        # defaults = {
        #     "code": Plan.Code.FREE,
        #     "name": "Free",
        #     "description": "Free plan",
        #     "is_active": True,
        # }
        # defaults.update(kwargs)
        plan, _ = Plan.objects.get_or_create(**kwargs)
        return plan

    @staticmethod
    def free():
        return PlanFactory.create(
            code=Plan.Code.FREE,
            name="Free",
        )

    @staticmethod
    def pro():
        return PlanFactory.create(
            code=Plan.Code.PRO,
            name="Pro",
        )