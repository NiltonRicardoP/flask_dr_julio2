import os
from datetime import datetime, date as dt_date, time as dt_time, timedelta

from models import Appointment

BOOKED_STATUSES = {"pending", "confirmed"}  # treat pending as reserved

DEFAULT_WORK_START = dt_time(8, 0)  # 08:00
DEFAULT_WORK_END = dt_time(17, 0)   # 17:00 (end exclusive)
DEFAULT_SLOT_MINUTES = 30
DEFAULT_CAPACITY = 1


def _parse_time_env(value: str | None, fallback: dt_time) -> dt_time:
    if not value:
        return fallback
    try:
        return dt_time.fromisoformat(value.strip())
    except ValueError:
        return fallback


def get_working_hours() -> tuple[dt_time, dt_time]:
    start = _parse_time_env(os.getenv("AVAIL_WORK_START"), DEFAULT_WORK_START)
    end = _parse_time_env(os.getenv("AVAIL_WORK_END"), DEFAULT_WORK_END)
    if end <= start:
        return DEFAULT_WORK_START, DEFAULT_WORK_END
    return start, end


def get_slot_minutes() -> int:
    value = os.getenv("AVAIL_SLOT_MINUTES")
    if not value:
        return DEFAULT_SLOT_MINUTES
    try:
        minutes = int(value)
    except ValueError:
        return DEFAULT_SLOT_MINUTES
    return minutes if minutes > 0 else DEFAULT_SLOT_MINUTES


def get_capacity_per_slot() -> int:
    value = os.getenv("AVAIL_CAPACITY")
    if not value:
        return DEFAULT_CAPACITY
    try:
        capacity = int(value)
    except ValueError:
        return DEFAULT_CAPACITY
    return max(1, capacity)


def is_valid_slot(day: dt_date, slot_time: dt_time) -> bool:
    start, end = get_working_hours()
    if slot_time < start or slot_time >= end:
        return False
    slot_minutes = get_slot_minutes()
    start_dt = datetime.combine(day, start)
    slot_dt = datetime.combine(day, slot_time)
    delta = (slot_dt - start_dt).total_seconds()
    return delta % (slot_minutes * 60) == 0


def get_booked_count(day: dt_date, slot_time: dt_time, exclude_id: int | None = None) -> int:
    query = Appointment.query.filter(
        Appointment.date == day,
        Appointment.time == slot_time,
        Appointment.status.in_(list(BOOKED_STATUSES)),
    )
    if exclude_id:
        query = query.filter(Appointment.id != exclude_id)
    return query.count()


def is_slot_available(day: dt_date, slot_time: dt_time, exclude_id: int | None = None) -> bool:
    if not is_valid_slot(day, slot_time):
        return False
    return get_booked_count(day, slot_time, exclude_id=exclude_id) < get_capacity_per_slot()


def _iter_slots(day: dt_date):
    start, end = get_working_hours()
    slot_minutes = get_slot_minutes()
    start_dt = datetime.combine(day, start)
    end_dt = datetime.combine(day, end)
    cur = start_dt
    while cur < end_dt:
        yield cur.time()
        cur += timedelta(minutes=slot_minutes)


def get_slot_config() -> dict:
    start, end = get_working_hours()
    slot_minutes = get_slot_minutes()
    last_slot_dt = datetime.combine(dt_date.today(), end) - timedelta(minutes=slot_minutes)
    return {
        "work_start": start.strftime("%H:%M"),
        "work_end": end.strftime("%H:%M"),
        "slot_minutes": slot_minutes,
        "step": slot_minutes * 60,
        "last_slot": last_slot_dt.time().strftime("%H:%M"),
        "capacity": get_capacity_per_slot(),
    }


def get_availability(day: dt_date):
    appts = (
        Appointment.query
        .filter(Appointment.date == day)
        .filter(Appointment.status.in_(list(BOOKED_STATUSES)))
        .all()
    )

    booked_map = {}
    for appt in appts:
        booked_map[appt.time] = booked_map.get(appt.time, 0) + 1

    slots = []
    for slot_time in _iter_slots(day):
        booked = booked_map.get(slot_time, 0)
        capacity = get_capacity_per_slot()
        available = max(0, capacity - booked)
        slots.append({
            "time": slot_time.strftime("%H:%M"),
            "capacity": capacity,
            "booked": booked,
            "available": available,
        })

    return {"date": day.strftime("%Y-%m-%d"), "slots": slots}
