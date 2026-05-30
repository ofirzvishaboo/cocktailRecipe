"""Availability collection deadlines (due by Tuesday before the schedule week)."""
from datetime import date, datetime, timedelta, timezone


def availability_deadline_for_week(week_start_sunday: date) -> date:
    """Tuesday before the Sunday that starts the schedule week."""
    return week_start_sunday - timedelta(days=5)


def staff_may_submit_availability(week_start_sunday: date, on_date: date | None = None) -> bool:
    """Staff may submit through end of the deadline Tuesday (inclusive)."""
    today = on_date or datetime.now(timezone.utc).date()
    return today <= availability_deadline_for_week(week_start_sunday)


def default_target_week_start(on_date: date | None = None) -> date:
    """Sunday of the week staff should be filling in now."""
    today = on_date or datetime.now(timezone.utc).date()
    wd = today.weekday()  # Mon=0 .. Sun=6
    days_until_sunday = (6 - wd) % 7
    if wd == 6:
        sunday = today
    else:
        sunday = today + timedelta(days=days_until_sunday)
    if staff_may_submit_availability(sunday, today):
        return sunday
    return sunday + timedelta(days=7)
