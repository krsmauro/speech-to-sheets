from datetime import UTC, date, datetime

from speech_to_sheets.sheets.dates import to_serial, today_in


def test_serial_numbers_match_the_sheet() -> None:
    # Known values in Google Sheets and Excel: 1 March 1900 is 61, 1 January 2000 is 36526.
    assert to_serial(date(1899, 12, 31)) == 1
    assert to_serial(date(1900, 3, 1)) == 61
    assert to_serial(date(2000, 1, 1)) == 36526


def test_today_follows_the_configured_timezone() -> None:
    utc_night = datetime(2026, 10, 26, 3, 0, tzinfo=UTC)
    assert today_in("America/New_York", utc_night) == date(2026, 10, 25)
    assert today_in("UTC", utc_night) == date(2026, 10, 26)
    assert today_in("Asia/Tokyo", utc_night) == date(2026, 10, 26)


def test_today_without_a_given_time_uses_the_clock() -> None:
    assert today_in("UTC") == datetime.now(UTC).date()
