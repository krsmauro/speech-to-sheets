from datetime import date, datetime
from zoneinfo import ZoneInfo

# Day zero of sheet serial numbers (the same as Excel's 1900 date system after 1 March 1900).
SERIAL_EPOCH = date(1899, 12, 30)


def today_in(timezone: str, now: datetime | None = None) -> date:
    """Today's date in the configured timezone. Never taken from what the user said."""
    zone = ZoneInfo(timezone)
    return (now or datetime.now(zone)).astimezone(zone).date()


def to_serial(day: date) -> int:
    """A date as a serial number: the sheet's own date format shows it, so no locale can
    read 05/10 as May 10."""
    return (day - SERIAL_EPOCH).days
