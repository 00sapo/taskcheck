import pytest
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "time_maps": {
            "work": {
                "monday": [[9.0, 17.0]],
                "tuesday": [[9.0, 17.0]],
                "wednesday": [[9.0, 17.0]],
                "thursday": [[9.0, 17.0]],
                "friday": [[9.0, 17.0]],
                "saturday": [],
                "sunday": []
            },
            "personal": {
                "monday": [[18.0, 22.0]],
                "tuesday": [[18.0, 22.0]],
                "wednesday": [[18.0, 22.0]],
                "thursday": [[18.0, 22.0]],
                "friday": [[18.0, 22.0]],
                "saturday": [[10.0, 18.0]],
                "sunday": [[10.0, 18.0]]
            }
        },
        "scheduler": {
            "days_ahead": 7,
            "weight_urgency": 1.0,
            "urgency_epsilon": 0.1,
            "max_top_urgency_rounds": 10,
            "n_undos": 1,
            "weight_due_date": 0.0
        },
        "calendars": {
            "work_calendar": {
                "url": "https://example.com/calendar.ics",
                "event_all_day_is_blocking": True,
                "expiration": 0.25,
                "timezone": "UTC"
            }
        },
        "report": {
            "include_unplanned": True,
            "additional_attributes": ["urgency", "priority"],
            "additional_attributes_unplanned": ["urgency", "due"],
            "emoji_keywords": {
                "meeting": ":busts_in_silhouette:",
                "code": ":computer:"
            }
        }
    }


@pytest.fixture
def sample_tasks():
    """Sample task data for testing."""
    return [
        {
            "id": 1,
            "uuid": "task-1-uuid",
            "description": "Write documentation",
            "estimated": "P2H",
            "time_map": "work",
            "urgency": 10.5,
            "status": "pending",
            "project": "docs",
            "entry": "20231201T090000Z"
        },
        {
            "id": 2,
            "uuid": "task-2-uuid",
            "description": "Code review meeting",
            "estimated": "P1H",
            "time_map": "work",
            "urgency": 15.2,
            "status": "pending",
            "project": "dev",
            "entry": "20231201T100000Z",
            "due": "20231210T170000Z"
        },
        {
            "id": 3,
            "uuid": "task-3-uuid",
            "description": "Personal project",
            "estimated": "P3H",
            "time_map": "personal",
            "urgency": 5.0,
            "status": "pending",
            "project": "hobby",
            "entry": "20231201T110000Z"
        }
    ]


@pytest.fixture
def sample_calendar_events():
    """Sample calendar events for testing."""
    today = datetime.now().date()
    return [
        {
            "start": (datetime.combine(today, datetime.min.time()) + timedelta(hours=14)).isoformat(),
            "end": (datetime.combine(today, datetime.min.time()) + timedelta(hours=15)).isoformat()
        },
        {
            "start": (datetime.combine(today + timedelta(days=1), datetime.min.time()) + timedelta(hours=10)).isoformat(),
            "end": (datetime.combine(today + timedelta(days=1), datetime.min.time()) + timedelta(hours=11)).isoformat()
        }
    ]


@pytest.fixture
def test_taskrc():
    """Provide a consistent test taskrc path."""
    return "/tmp/taskcheck/"


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for Taskwarrior commands."""
    with patch('subprocess.run') as mock_run:
        yield mock_run


@pytest.fixture
def mock_task_export(sample_tasks):
    """Mock task export command."""
    def _mock_run(cmd, **kwargs):
        mock_result = Mock()
        if cmd == ["task", "export"]:
            mock_result.stdout = json.dumps(sample_tasks)
        elif cmd[0] == "task" and "_show" in cmd:
            mock_result.stdout = """urgency.uda.estimated.P1H.coefficient=5.0
urgency.uda.estimated.P2H.coefficient=8.0
urgency.uda.estimated.P3H.coefficient=10.0
urgency.inherit=1
urgency.active.coefficient=4.0
urgency.age.max=365
urgency.due.coefficient=12.0
urgency.age.coefficient=2.0"""
        else:
            mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0
        return mock_result
    
    with patch('subprocess.run', side_effect=_mock_run):
        yield


@pytest.fixture
def mock_task_export_with_taskrc(sample_tasks, test_taskrc):
    """Mock task export command with taskrc verification."""
    def _mock_run(cmd, **kwargs):
        # Verify environment is passed correctly when using taskrc
        env = kwargs.get('env')
        if env and 'TASKRC' in env:
            assert env['TASKRC'] == test_taskrc
            assert env['TASKDATA'] == test_taskrc
        
        mock_result = Mock()
        if cmd == ["task", "export"]:
            mock_result.stdout = json.dumps(sample_tasks)
        elif cmd[0] == "task" and "_show" in cmd:
            mock_result.stdout = """urgency.uda.estimated.P1H.coefficient=5.0
urgency.uda.estimated.P2H.coefficient=8.0
urgency.uda.estimated.P3H.coefficient=10.0
urgency.inherit=1
urgency.active.coefficient=4.0
urgency.age.max=365
urgency.due.coefficient=12.0
urgency.age.coefficient=2.0"""
        else:
            mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0
        return mock_result
    
    with patch('subprocess.run', side_effect=_mock_run):
        yield


@pytest.fixture
def temp_cache_dir():
    """Temporary directory for cache testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('taskcheck.ical.CACHE', Path(temp_dir)):
            yield Path(temp_dir)


@pytest.fixture
def mock_ical_response():
    """Mock iCal response data."""
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:test
BEGIN:VEVENT
UID:test-event-1
DTSTART:20231205T140000Z
DTEND:20231205T150000Z
SUMMARY:Test Meeting
END:VEVENT
BEGIN:VEVENT
UID:test-event-2
DTSTART:20231206T100000Z
DTEND:20231206T110000Z
SUMMARY:Another Meeting
RRULE:FREQ=WEEKLY;COUNT=3
END:VEVENT
END:VCALENDAR"""
