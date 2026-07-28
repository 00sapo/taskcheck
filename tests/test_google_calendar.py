from unittest.mock import Mock, patch

from taskcheck.google_calendar import _safe_account_id, render_calendar_config
from taskcheck.__main__ import main


def test_safe_account_id():
    assert _safe_account_id("foo.bar@example.com") == "foo_bar_example_com"


@patch("taskcheck.google_calendar.get_token_path")
def test_render_calendar_config(mock_token_path):
    mock_token_path.return_value = "/tmp/task/google/foo.token.json"
    cfg = render_calendar_config("foo", {"id": "abc123"}, taskrc="/tmp/task")
    assert "[calendars.foo.abc123]" in cfg
    assert "calendar_id = \"abc123\"" in cfg


@patch("taskcheck.google_calendar.add_google_calendar")
@patch("taskcheck.__main__.arg_parser.parse_args")
def test_main_add_google_calendar(mock_args, mock_add):
    mock_args.return_value = Mock(
        install=False,
        add_google_calendar=True,
        schedule=False,
        report=None,
        verbose=False,
        force_update=False,
        taskrc="/tmp/task",
        urgency_weight=None,
        dry_run=False,
        auto_adjust_urgency=True,
    )
    main()
    mock_add.assert_called_once_with(taskrc="/tmp/task")
