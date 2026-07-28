import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from taskcheck.ical import fetch_ical_data, parse_ical_events, ical_to_dict, get_cache_filename


class TestIcalFetching:
    @patch("requests.get")
    def test_fetch_ical_data_success(self, mock_get, mock_ical_response):
        mock_response = Mock()
        mock_response.text = mock_ical_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        assert fetch_ical_data("https://example.com/calendar.ics") == mock_ical_response

    @patch("requests.get")
    def test_fetch_ical_data_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_get.return_value = mock_response

        with pytest.raises(Exception):
            fetch_ical_data("https://example.com/calendar.ics")


class TestIcalParsing:
    @patch("taskcheck.ical.datetime")
    def test_parse_ical_events_simple(self, mock_datetime, mock_ical_response):
        mock_datetime.now.return_value = datetime(2023, 12, 1, 12, 0, 0)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        events = parse_ical_events(mock_ical_response, days_ahead=7, all_day=False)
        assert len(events) == 2

    @patch("taskcheck.ical.datetime")
    def test_parse_ical_events_with_timezone(self, mock_datetime, mock_ical_response):
        mock_datetime.now.return_value = datetime(2023, 12, 1, 12, 0, 0)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        events = parse_ical_events(mock_ical_response, days_ahead=7, all_day=False, tz_name="America/New_York")
        assert events and events[0]["start"].endswith(("-05:00", "-04:00"))

    @patch("taskcheck.ical.datetime")
    def test_parse_ical_events_recurring(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2023, 12, 1, 12, 0, 0)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        ical_text = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:test
BEGIN:VEVENT
UID:recurring-event
DTSTART:20231205T140000Z
DTEND:20231205T150000Z
SUMMARY:Weekly Meeting
RRULE:FREQ=WEEKLY;COUNT=3
END:VEVENT
END:VCALENDAR"""
        assert len(parse_ical_events(ical_text, days_ahead=21, all_day=False)) == 3

    @patch("taskcheck.ical.datetime")
    def test_parse_ical_events_all_day(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2023, 12, 1, 12, 0, 0)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        ical_text = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:test
BEGIN:VEVENT
UID:all-day-event
DTSTART;VALUE=DATE:20231205
DTEND;VALUE=DATE:20231206
SUMMARY:All Day Event
END:VEVENT
END:VCALENDAR"""
        assert len(parse_ical_events(ical_text, days_ahead=7, all_day=True)) == 1
        assert parse_ical_events(ical_text, days_ahead=7, all_day=False) == []

    @patch("taskcheck.ical.datetime")
    def test_parse_multi_day_all_day_event_preserves_span(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2023, 12, 1, 12, 0, 0)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        ical_text = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:test
BEGIN:VEVENT
UID:multi-day-event
DTSTART;VALUE=DATE:20231205
DTEND;VALUE=DATE:20231207
SUMMARY:Two Day Event
END:VEVENT
END:VCALENDAR"""
        events = parse_ical_events(ical_text, days_ahead=7, all_day=True)
        assert events == [{"start": "2023-12-05T00:00:00", "end": "2023-12-07T00:00:00"}]

    @patch("taskcheck.ical.datetime")
    def test_parse_ical_events_exdate_and_recurrence_id(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2023, 12, 1, 12, 0, 0)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        ical_text = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:test
BEGIN:VEVENT
UID:rrule-exdate
DTSTART:20231205T140000Z
DTEND:20231205T150000Z
RRULE:FREQ=DAILY;COUNT=3
EXDATE:20231206T140000Z
END:VEVENT
BEGIN:VEVENT
UID:rrule-exception
RECURRENCE-ID:20231207T140000Z
DTSTART:20231207T160000Z
DTEND:20231207T170000Z
END:VEVENT
END:VCALENDAR"""
        events = parse_ical_events(ical_text, days_ahead=10, all_day=False)
        starts = {e["start"] for e in events}
        assert len(events) == 2
        assert any("2023-12-05T14:00:00+00:00" in s for s in starts)
        assert any("2023-12-07T16:00:00+00:00" in s for s in starts)

    @patch("taskcheck.ical.datetime")
    def test_parse_ical_events_past_until_skipped(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2023, 12, 10, 12, 0, 0)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        ical_text = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:test
BEGIN:VEVENT
UID:past-rule
DTSTART:20231201T140000Z
DTEND:20231201T150000Z
RRULE:FREQ=DAILY;UNTIL=20231205T000000Z
END:VEVENT
END:VCALENDAR"""
        assert parse_ical_events(ical_text, days_ahead=7, all_day=False) == []


class TestIcalCaching:
    def test_get_cache_filename(self):
        filename = get_cache_filename("https://example.com/calendar.ics")
        assert filename.suffix == ".json"
        assert len(filename.stem) == 64

    @patch("requests.get")
    def test_ical_to_dict_with_cache(self, mock_get, temp_cache_dir, mock_ical_response):
        mock_response = Mock()
        mock_response.text = mock_ical_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        url = "https://example.com/calendar.ics"
        events1 = ical_to_dict(url, days_ahead=7, all_day=False, expiration=1.0)
        events2 = ical_to_dict(url, days_ahead=7, all_day=False, expiration=1.0)
        assert events1 == events2
        assert mock_get.call_count == 1

    @patch("requests.get")
    def test_ical_to_dict_force_update(self, mock_get, temp_cache_dir, mock_ical_response):
        mock_response = Mock()
        mock_response.text = mock_ical_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        url = "https://example.com/calendar.ics"
        events1 = ical_to_dict(url, days_ahead=7, all_day=False, expiration=1.0)
        events2 = ical_to_dict(url, days_ahead=7, all_day=False, expiration=1.0, force_update=True)
        assert events1 == events2
        assert mock_get.call_count == 2

    @patch("requests.get")
    def test_ical_to_dict_expired_cache_refreshes(self, mock_get, temp_cache_dir, mock_ical_response):
        mock_response = Mock()
        mock_response.text = mock_ical_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        url = "https://example.com/calendar.ics"
        ical_to_dict(url, days_ahead=7, all_day=False, expiration=1.0)
        ical_to_dict(url, days_ahead=7, all_day=False, expiration=0.0)
        assert mock_get.call_count == 2


class TestExceptionHandling:
    @patch("requests.get")
    def test_ical_to_dict_malformed_ical(self, mock_get, temp_cache_dir):
        mock_response = Mock()
        mock_response.text = "INVALID ICAL DATA"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with pytest.raises(Exception):
            ical_to_dict("https://example.com/calendar.ics", days_ahead=7, all_day=False)
