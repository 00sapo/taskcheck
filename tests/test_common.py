import pytest
from datetime import datetime, timedelta, time
from unittest.mock import patch, Mock
import json

from taskcheck.common import (
    hours_to_decimal,
    hours_to_time,
    time_to_decimal,
    get_available_hours,
    pdth_to_hours,
    hours_to_pdth,
    get_long_range_time_map,
    get_tasks,
    get_calendars,
    get_task_env,
    mark_end_date,
)


class TestTimeConversions:
    def test_hours_to_decimal(self):
        assert hours_to_decimal(9.0) == 9.0
        assert abs(hours_to_decimal(9.30) - 9.5) < 1e-10  # 9:30 -> 9.5 hours
        assert abs(hours_to_decimal(9.15) - 9.25) < 1e-10  # 9:15 -> 9.25 hours
        
    def test_hours_to_time(self):
        assert hours_to_time(9.0) == time(9, 0)
        assert hours_to_time(9.30) == time(9, 30)  # 9.30 means 9:30
        assert hours_to_time(14.15) == time(14, 15)  # 14.15 means 14:15
        
    def test_time_to_decimal(self):
        assert time_to_decimal(time(9, 0)) == 9.0
        assert time_to_decimal(time(9, 30)) == 9.5
        assert time_to_decimal(time(14, 15)) == 14.25


class TestTaskUpdates:
    @patch("taskcheck.common.subprocess.run")
    def test_mark_end_date_passes_unquoted_scheduling_value(self, mock_run):
        mark_end_date(
            None,
            "2026-07-29",
            "2026-07-28",
            "2026-07-28 - PT1H\n2026-07-29 - PT1H",
            1,
        )

        command = mock_run.call_args.args[0]
        assert command[-1] == (
            "scheduling:2026-07-28 - PT1H\n2026-07-29 - PT1H"
        )


class TestDurationConversions:
    def test_pdth_to_hours(self):
        assert pdth_to_hours("P1H") == 1.0
        assert pdth_to_hours("P2H30M") == 2.5
        assert pdth_to_hours("P1DT2H") == 26.0
        assert pdth_to_hours("PT30M") == 0.5
        assert pdth_to_hours("P1D") == 24.0
        
    def test_hours_to_pdth(self):
        assert hours_to_pdth(1.0) == "PT1H"
        assert hours_to_pdth(2.5) == "PT2H30M"
        assert hours_to_pdth(26.0) == "P1DT2H"
        assert hours_to_pdth(0.5) == "PT30M"
        assert hours_to_pdth(24.0) == "P1DT"


class TestAvailableHours:
    def test_get_available_hours_no_events(self, sample_config):
        date = datetime(2023, 12, 5).date()  # Tuesday
        time_map = sample_config["time_maps"]["work"]
        calendars = []
        
        available = get_available_hours(time_map, date, calendars)
        assert available == 8.0  # 9-17 = 8 hours
        
    def test_get_available_hours_with_blocking_event(self, sample_config):
        date = datetime(2023, 12, 5).date()  # Tuesday
        time_map = sample_config["time_maps"]["work"]
        
        # Event from 14:00 to 15:00
        calendars = [[{
            "start": datetime(2023, 12, 5, 14, 0),
            "end": datetime(2023, 12, 5, 15, 0)
        }]]
        
        available = get_available_hours(time_map, date, calendars, verbose=True)
        assert available == 7.0  # 8 hours - 1 hour blocked
        
    def test_get_available_hours_weekend(self, sample_config):
        date = datetime(2023, 12, 3).date()  # Sunday
        time_map = sample_config["time_maps"]["work"]
        calendars = []
        
        available = get_available_hours(time_map, date, calendars)
        assert available == 0.0

    def test_get_available_hours_multi_day_all_day_event(self, sample_config):
        time_map = sample_config["time_maps"]["work"]
        calendars = [[{
            "start": datetime(2023, 12, 5, 0, 0),
            "end": datetime(2023, 12, 7, 0, 0),
        }]]

        assert get_available_hours(time_map, datetime(2023, 12, 5).date(), calendars) == 0.0
        assert get_available_hours(time_map, datetime(2023, 12, 6).date(), calendars) == 0.0
        assert get_available_hours(time_map, datetime(2023, 12, 7).date(), calendars) == 8.0


class TestLongRangeTimeMap:
    def test_get_long_range_time_map(self, sample_config, sample_calendar_events):
        time_maps = sample_config["time_maps"]
        time_map_names = ["work"]
        days_ahead = 3
        calendars = [sample_calendar_events]
        
        task_time_map, today_used_hours = get_long_range_time_map(
            time_maps, time_map_names, days_ahead, calendars
        )
        
        assert len(task_time_map) == days_ahead
        assert all(isinstance(hours, (int, float)) for hours in task_time_map)
        assert isinstance(today_used_hours, (int, float))


class TestGetTasks:
    def test_get_tasks(self, mock_task_export_with_taskrc, sample_tasks, test_taskrc):
        tasks = get_tasks(taskrc=test_taskrc)
        
        # Should only return tasks with estimated field
        estimated_tasks = [t for t in tasks if "estimated" in t]
        assert len(estimated_tasks) == len(sample_tasks)
        
        # Should be sorted by urgency (descending)
        urgencies = [t["urgency"] for t in tasks]
        assert urgencies == sorted(urgencies, reverse=True)


class TestGetCalendars:
    @patch('taskcheck.common.ical_to_dict')
    def test_get_calendars(self, mock_ical, sample_config, sample_calendar_events):
        mock_ical.return_value = sample_calendar_events
        
        calendars = get_calendars(sample_config)
        
        assert len(calendars) == 1
        assert calendars[0] == sample_calendar_events
        mock_ical.assert_called_once()

    @patch("taskcheck.google_calendar.google_calendar_to_dict")
    @patch("taskcheck.common.ical_to_dict")
    def test_get_google_calendars(
        self, mock_ical, mock_google, sample_config, sample_calendar_events
    ):
        sample_config["calendars"] = {
            "google": {
                "url": "google://primary",
                "provider": "google",
                "calendar_id": "primary",
                "token_path": "/tmp/google.token.json",
                "event_all_day_is_blocking": True,
                "expiration": 0.25,
            }
        }
        mock_google.return_value = sample_calendar_events

        calendars = get_calendars(sample_config)

        assert calendars == [sample_calendar_events]
        mock_google.assert_called_once_with(
            "primary", "/tmp/google.token.json", 7, all_day=True
        )
        mock_ical.assert_not_called()


class TestEnvironmentVariables:
    def test_get_task_env_sets_both_variables(self, test_taskrc):
        """Test that get_task_env sets both TASKDATA and TASKRC."""
        env = get_task_env(taskrc=test_taskrc)
        
        assert env['TASKDATA'] == test_taskrc
        assert env['TASKRC'] == test_taskrc
        
    def test_get_task_env_without_taskrc(self):
        """Test that get_task_env returns unchanged environment when taskrc=None."""
        import os
        original_env = os.environ.copy()
        env = get_task_env(taskrc=None)
        
        # Should not add TASKDATA or TASKRC if not specified
        assert env == original_env
