"""Seed default shift templates and bar settings."""
import uuid
from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.schedule import BarScheduleSettings, ShiftTemplate


async def ensure_schedule_defaults(db: AsyncSession) -> None:
    res = await db.execute(select(BarScheduleSettings).where(BarScheduleSettings.id == 1))
    if res.scalar_one_or_none() is None:
        db.add(
            BarScheduleSettings(
                id=1,
                week_starts_on=6,
                friday_last_start_hour=18,
                saturday_closed=True,
            )
        )

    tpl_res = await db.execute(select(ShiftTemplate.id).limit(1))
    if tpl_res.scalar_one_or_none() is not None:
        await db.flush()
        return

    defaults = [
        ("Open", time(17, 0), time(23, 0), 1),
        ("Close", time(20, 0), time(1, 0), 2),
        ("Day", time(12, 0), time(18, 0), 0),
    ]
    for name, start, end, order in defaults:
        db.add(
            ShiftTemplate(
                id=uuid.uuid4(),
                name=name,
                start_time=start,
                end_time=end,
                sort_order=order,
                active=True,
            )
        )
    await db.flush()
