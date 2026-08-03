from datetime import date

from rich.console import Console

from taskcheck.timeline import (
    build_timeline,
    detect_theme,
    parse_scheduling_dates,
    project_color,
    select_zoom,
)


def render(renderable):
    console = Console(width=200, record=True, color_system=None)
    console.print(renderable)
    return console.export_text()


def test_parse_scheduling_dates_ignores_invalid_lines():
    task = {"scheduling": "2024-01-02 - PT2H\ninvalid\n2024-01-03 - PT30M"}

    assert parse_scheduling_dates(task) == [date(2024, 1, 2), date(2024, 1, 3)]


def test_day_timeline_groups_projects_and_marks_events():
    tasks = [
        {
            "id": 1,
            "project": "work.client",
            "description": "Build feature",
            "scheduling": "2024-01-01 - PT2H\n2024-01-02 - PT2H\n2024-01-03 - PT1H",
            "due": "20240102T170000Z",
        },
        {
            "id": 2,
            "project": "home",
            "description": "Repair shelf",
            "scheduling": "2024-01-02 - PT1H",
        },
    ]

    output = render(
        build_timeline(tasks, date(2024, 1, 1), date(2024, 1, 3), "day", "dark")
    )

    assert "▶ start" in output
    assert "━ work" in output
    assert "◀ end" in output
    assert "◆ deadline" in output
    assert "work" in output
    assert "  client" in output
    assert "#1 Build feature" in output
    assert "▶━━│━◆━│━━◀" in output
    assert "▶━◀" in output


def test_select_zoom_uses_the_most_detailed_view_that_fits():
    start = date(2024, 1, 1)
    end = date(2024, 1, 31)

    assert select_zoom(start, end, 200, 20) == "day"
    assert select_zoom(start, end, 80, 20) == "week"
    assert select_zoom(start, end, 40, 20) == "month"


def test_day_boundaries_distinguish_week_and_month():
    output = render(
        build_timeline([], date(2024, 1, 28), date(2024, 2, 2), "day", "dark")
    )

    assert "┃" in output  # week boundary
    assert "║" in output  # month boundary
    assert "│" in output  # day boundary


def test_week_and_month_zoom_aggregate_events():
    tasks = [
        {
            "id": 1,
            "project": "work",
            "description": "Long task",
            "scheduling": "2024-01-30 - PT1H\n2024-02-12 - PT1H",
            "due": "20240215T120000Z",
        }
    ]

    week = render(
        build_timeline(tasks, date(2024, 1, 29), date(2024, 2, 18), "week", "dark")
    )
    month = render(
        build_timeline(tasks, date(2024, 1, 1), date(2024, 2, 29), "month", "dark")
    )

    assert "W05" in week and "W07" in week
    assert "Jan 2024" in month and "Feb 2024" in month
    assert "▶" in week and "◀" in week and "◆" in week
    assert "▶" in month and "◀" in month and "◆" in month


def test_auto_zoom_uses_available_columns():
    output = render(
        build_timeline([], date(2024, 1, 1), date(2024, 1, 31), columns=80)
    )

    assert "Timeline · week" in output


def test_build_timeline_uses_config_theme():
    output = render(
        build_timeline([], date(2024, 1, 1), date(2024, 1, 1), "day", config={"theme": "light"})
    )

    assert "Timeline · day" in output


def test_theme_detection_and_project_colors(monkeypatch):
    monkeypatch.setattr("taskcheck.theme._probe_osc11_background", lambda: "light")
    assert detect_theme() == "light"
    monkeypatch.setattr("taskcheck.theme._probe_osc11_background", lambda: None)
    monkeypatch.setenv("COLORFGBG", "0;15")
    assert detect_theme() == "light"
    monkeypatch.setenv("COLORFGBG", "15;0")
    assert detect_theme() == "dark"
    assert detect_theme(config={"theme": "light"}) == "light"
    assert detect_theme(config={"theme": "dark"}) == "dark"

    assert project_color("work", "dark") == project_color("work", "dark")
    assert project_color("work", "dark") != project_color("home", "dark")
    assert project_color("work", "dark") != project_color("work", "light")
