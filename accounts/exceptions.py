class LimitExceeded(Exception):
    def __init__(self, message="Too many requests.", *, retry_after: int | None = None, scope: str | None = None):
        self.retry_after = retry_after
        self.scope = scope
        super().__init__(message)


class RateLimitExceeded(LimitExceeded):
    pass


class TokenRefreshTooOften(RateLimitExceeded):
    def __init__(self, retry_after):
        retry_after_seconds = int(retry_after.total_seconds())
        super().__init__(
            "Token refresh rate limit exceeded",
            retry_after=retry_after_seconds,
            scope="token_refresh",
        )
