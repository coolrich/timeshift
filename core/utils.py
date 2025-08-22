from datetime import datetime, timezone
from typing import Tuple, Optional


class TimeService:

    @staticmethod
    def validate_time_format(time_str: str) -> Tuple[bool, Optional[datetime]]:
        try:
            dt = datetime.fromisoformat(time_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return True, dt
        except (ValueError, TypeError):
            return False, None
