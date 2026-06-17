class LimitExceeded(Exception):
    def __init__(self, message="Too many requests", *,
                 retry_after: int | None = None,
                 total_seconds: int | None = None,
                 scope: str | None = None,
                 period: str | None = None,
                 ):
        self.retry_after = retry_after
        self.scope = scope
        self.total_seconds = total_seconds
        self.period = period
        super().__init__(message)


class RateLimitExceeded(LimitExceeded):
    pass


# TODO: check this exception
class TokenRefreshTooOften(RateLimitExceeded):
    def __init__(self,
                 retry_after: int | None= None,
                 total_seconds: int | None= None,
                 period: str | None = None):
        super().__init__(
            "Token refresh rate limit exceeded",
            retry_after=retry_after,
            scope="token_refresh",
            total_seconds=total_seconds,
            period=period
        )
