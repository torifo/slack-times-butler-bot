from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


def now_jst() -> datetime:
    return datetime.now(tz=JST)


def is_business_day(day: date) -> bool:
    if day.weekday() >= 5:
        return False
    return day not in japanese_holidays(day.year)


def is_last_business_day_of_week(day: date) -> bool:
    if not is_business_day(day):
        return False
    current = day + timedelta(days=1)
    while current.weekday() <= 4:
        if is_business_day(current):
            return False
        current += timedelta(days=1)
    return True


def japanese_holidays(year: int) -> set[date]:
    holidays = _base_holidays(year)
    observed: set[date] = set()
    for holiday in sorted(holidays):
        if holiday.weekday() != 6:
            continue
        substitute = holiday + timedelta(days=1)
        while substitute in holidays or substitute in observed:
            substitute += timedelta(days=1)
        observed.add(substitute)
    holidays |= observed

    start = date(year, 1, 1)
    end = date(year, 12, 31)
    current = start
    while current <= end:
        prev_day = current - timedelta(days=1)
        next_day = current + timedelta(days=1)
        if (
            current.weekday() < 5
            and current not in holidays
            and prev_day in holidays
            and next_day in holidays
        ):
            holidays.add(current)
        current += timedelta(days=1)
    return holidays


def _base_holidays(year: int) -> set[date]:
    holidays = {
        date(year, 1, 1),
        _coming_of_age_day(year),
        date(year, 2, 11),
        _emperors_birthday(year),
        _vernal_equinox_day(year),
        date(year, 4, 29),
        date(year, 5, 3),
        date(year, 5, 4),
        date(year, 5, 5),
        _marine_day(year),
        date(year, 8, 11),
        _respect_for_the_aged_day(year),
        _autumnal_equinox_day(year),
        _sports_day(year),
        date(year, 11, 3),
        date(year, 11, 23),
    }
    return holidays


def _nth_weekday(year: int, month: int, weekday: int, nth: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (nth - 1))


def _coming_of_age_day(year: int) -> date:
    if year >= 2000:
        return _nth_weekday(year, 1, 0, 2)
    return date(year, 1, 15)


def _marine_day(year: int) -> date:
    if year >= 2003:
        return _nth_weekday(year, 7, 0, 3)
    return date(year, 7, 20)


def _respect_for_the_aged_day(year: int) -> date:
    if year >= 2003:
        return _nth_weekday(year, 9, 0, 3)
    return date(year, 9, 15)


def _sports_day(year: int) -> date:
    if year >= 2000:
        return _nth_weekday(year, 10, 0, 2)
    return date(year, 10, 10)


def _emperors_birthday(year: int) -> date:
    if year >= 2020:
        return date(year, 2, 23)
    if 1989 <= year <= 2018:
        return date(year, 12, 23)
    return date(year, 4, 29)


def _vernal_equinox_day(year: int) -> date:
    day = math.floor(20.8431 + 0.242194 * (year - 1980) - math.floor((year - 1980) / 4))
    return date(year, 3, day)


def _autumnal_equinox_day(year: int) -> date:
    day = math.floor(23.2488 + 0.242194 * (year - 1980) - math.floor((year - 1980) / 4))
    return date(year, 9, day)
