class RateLimitExceeded(Exception):
    retry_after: int


class TokenRefreshTooOften(RateLimitExceeded):
    def __init__(self, retry_after):
        self.retry_after = int(retry_after.total_seconds())
        super().__init__("Token refresh rate limit exceeded")
