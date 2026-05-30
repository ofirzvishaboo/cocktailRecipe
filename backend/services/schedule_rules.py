"""Bar schedule business rules (closed hours, template eligibility)."""
from datetime import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from db.schedule import ShiftTemplate

# day_of_week: 0=Sunday .. 6=Saturday
SATURDAY = 6
FRIDAY = 5


def is_day_open(day_of_week: int, *, saturday_closed: bool = True) -> bool:
    if day_of_week == SATURDAY and saturday_closed:
        return False
    return True


def _time_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def template_allowed_on_day(
    template: "ShiftTemplate",
    day_of_week: int,
    *,
    friday_last_start_hour: int = 18,
    saturday_closed: bool = True,
) -> bool:
    if not is_day_open(day_of_week, saturday_closed=saturday_closed):
        return False
    if day_of_week != FRIDAY:
        return True

    start_m = _time_minutes(template.start_time)
    end_m = _time_minutes(template.end_time)
    cutoff = friday_last_start_hour * 60

    if start_m >= cutoff:
        return False
    # Shift must end by cutoff (no overnight Friday shifts)
    if end_m <= start_m:
        return False
    if end_m > cutoff:
        return False
    return True
