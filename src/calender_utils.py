from datetime import datetime, timedelta
import pytz

def parse_busy_slots(busy_slots, tz):
    return [
        (
            pytz.timezone(tz).localize(datetime.fromisoformat(start)),
            pytz.timezone(tz).localize(datetime.fromisoformat(end))
        )
        for start, end in busy_slots
    ]

def get_working_hours(day, working_hours, tz):
    tzinfo = pytz.timezone(tz)
    start = tzinfo.localize(datetime.fromisoformat(f"{day}T{working_hours[0]}"))
    end = tzinfo.localize(datetime.fromisoformat(f"{day}T{working_hours[1]}"))
    return start, end

def get_free_slots(working_start, working_end, busy_slots, slot_length=timedelta(minutes=30)):
    free = []
    current = working_start
    for b_start, b_end in sorted(busy_slots):
        if current + slot_length <= b_start:
            free.append((current, b_start))
        current = max(current, b_end)
    if current + slot_length <= working_end:
        free.append((current, working_end))
    return free
