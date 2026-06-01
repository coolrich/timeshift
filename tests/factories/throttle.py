# accounts/factories/throttle.py

from accounts.models import ThrottleRule

THROTTLE_CREATE_CLOCKS_LIMIT = 5
THROTTLE_GLOBAL_LIMIT = 60


class ThrottleFactory:
    @staticmethod
    def create(plan, **kwargs):
        # defaults = {
        #     "scope": ThrottleRule.Scope.CLOCKS_CREATE,
        #     "max_requests": 60,
        #     "period": ThrottleRule.Period.MINUTE,
        # }
        # defaults.update(kwargs)

        tr, _ = ThrottleRule.objects.get_or_create(
            plan=plan,
            **kwargs
        )
        return tr

    @staticmethod
    def clocks_create_scope(plan,
                            max_requests=THROTTLE_CREATE_CLOCKS_LIMIT,
                            period=ThrottleRule.Period.MINUTE
                            ):
        return ThrottleFactory.create(
            plan=plan,
            scope=ThrottleRule.Scope.CLOCKS_CREATE,
            max_requests=max_requests,
            period=period
        )

    @staticmethod
    def global_scope(plan,
                     max_requests=THROTTLE_CREATE_CLOCKS_LIMIT,
                     period=ThrottleRule.Period.MINUTE
                     ):
        return ThrottleFactory.create(
            plan=plan,
            scope=ThrottleRule.Scope.GLOBAL,
            max_requests=max_requests,
            period=period
        )
