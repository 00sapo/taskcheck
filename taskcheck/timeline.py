import colorsys
import hashlib
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from rich.console import Console, Group
from rich.text import Text

from taskcheck.report import (
    fetch_tasks,
    get_taskwarrior_date,
    parse_taskwarrior_timestamp,
)

SCHEDULING_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+-\s+P")


@dataclass(frozen=True)
class Period:
    start: date
    end: date
    label: str
    width: int


def detect_theme(environ=None, config=None):
    environ = os.environ if environ is None else environ
    config = config or {}
    for key in ("TASKCHECK_THEME", "PI_THEME"):
        value = environ.get(key, "").strip().lower()
        if value in {"light", "dark"}:
            return value
    value = str(config.get("theme", "")).strip().lower()
    if value in {"light", "dark"}:
        return value
    value = environ.get("COLORFGBG", "")
    try:
        background = int(value.split(";")[-1])
    except ValueError:
        return "dark"
    return "light" if background >= 8 else "dark"


def project_color(project, theme):
    digest = hashlib.sha256((project or "No project").encode()).digest()
    hue = int.from_bytes(digest[:3], "big") / 0xFFFFFF
    lightness = 0.32 if theme == "light" else 0.72
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, 0.68)
    return f"#{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}"


def parse_scheduling_dates(task):
    dates = []
    for line in task.get("scheduling", "").splitlines():
        match = SCHEDULING_DATE.match(line)
        if match:
            dates.append(date.fromisoformat(match.group(1)))
    return sorted(set(dates))


def _deadline(task):
    value = task.get("due")
    if not value:
        return None
    try:
        return parse_taskwarrior_timestamp(value).date()
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None


def _periods(start, end, zoom):
    periods = []
    current = start
    if zoom == "week":
        current -= timedelta(days=current.weekday())
    elif zoom == "month":
        current = current.replace(day=1)

    while current <= end:
        if zoom == "day":
            period_end = current
            label = current.strftime("%d")
            width = 3
            next_period = current + timedelta(days=1)
        elif zoom == "week":
            period_end = current + timedelta(days=6)
            label = f"W{current.isocalendar().week:02d}"
            width = 5
            next_period = current + timedelta(days=7)
        else:
            if current.month == 12:
                next_period = date(current.year + 1, 1, 1)
            else:
                next_period = date(current.year, current.month + 1, 1)
            period_end = next_period - timedelta(days=1)
            label = current.strftime("%b %Y")
            width = 8
        periods.append(Period(current, period_end, label, width))
        current = next_period
    return periods


def select_zoom(start, end, columns, label_width):
    for zoom in ("day", "week", "month"):
        periods = _periods(start, end, zoom)
        if label_width + sum(period.width + 1 for period in periods) <= columns:
            return zoom
    return "month"


def _separator(periods, index, zoom):
    if index == 0:
        return "║"
    current = periods[index].start
    previous = periods[index - 1].start
    if zoom == "month" or (current.year, current.month) != (
        previous.year,
        previous.month,
    ):
        return "║"
    if zoom == "week" or current.weekday() == 0:
        return "┃"
    return "│"


def _cell(task_dates, deadline, period):
    scheduled = [day for day in task_dates if period.start <= day <= period.end]
    starts = bool(task_dates) and period.start <= task_dates[0] <= period.end
    ends = bool(task_dates) and period.start <= task_dates[-1] <= period.end
    due = deadline is not None and period.start <= deadline <= period.end

    if starts and ends:
        core = "▶━◀"
    elif starts:
        core = "▶━━"
    elif ends:
        core = "━━◀"
    elif scheduled:
        core = "━━━"
    else:
        core = "   "
    if due:
        core = core[0] + "◆" + core[2]
    return core.center(period.width)


def _label(text, width):
    if len(text) <= width:
        return text.ljust(width)
    return text[: width - 1] + "…"


def _header(periods, label_width, zoom):
    lines = []
    if zoom in {"day", "week"}:
        context = Text(" " * label_width)
        previous_month = None
        for index, period in enumerate(periods):
            context.append(_separator(periods, index, zoom), style="dim")
            month = (period.start.year, period.start.month)
            label = period.start.strftime("%b") if month != previous_month else ""
            context.append(label.center(period.width), style="bold cyan")
            previous_month = month
        lines.append(context)

    line = Text(" " * label_width)
    for index, period in enumerate(periods):
        line.append(_separator(periods, index, zoom), style="dim")
        line.append(period.label.center(period.width), style="bold")
    lines.append(line)
    return lines


def build_timeline(
    tasks, start, end, zoom="auto", theme=None, config=None, columns=80
):
    if zoom not in {"auto", "day", "week", "month"}:
        raise ValueError(f"Unsupported zoom: {zoom}")
    planned = [(task, parse_scheduling_dates(task)) for task in tasks]
    planned = [(task, dates) for task, dates in planned if dates]
    planned.sort(key=lambda item: (item[0].get("project", ""), item[0].get("id", 0)))
    labels = [
        f"#{task.get('id', '?')} {task.get('description', '')}" for task, _ in planned
    ]
    label_width = min(36, max([20, *(len(label) + 6 for label in labels)]))
    zoom = select_zoom(start, end, columns, label_width) if zoom == "auto" else zoom
    periods = _periods(start, end, zoom)
    theme = theme or detect_theme(config=config)

    lines = [
        Text(
            f"Timeline · {zoom} · ▶ start · ━ work · ◀ end · ◆ deadline", style="bold"
        ),
        *_header(periods, label_width, zoom),
    ]
    previous_parts = []
    for task, dates in planned:
        project = task.get("project") or "No project"
        parts = project.split(".")
        common = 0
        while (
            common < min(len(parts), len(previous_parts))
            and parts[common] == previous_parts[common]
        ):
            common += 1
        for depth in range(common, len(parts)):
            path = ".".join(parts[: depth + 1])
            group = Text(
                _label("  " * depth + parts[depth], label_width),
                style=f"bold {project_color(path, theme)}",
            )
            for index, period in enumerate(periods):
                group.append(_separator(periods, index, zoom), style="dim")
                group.append(" " * period.width)
            lines.append(group)
        previous_parts = parts

        color = project_color(project, theme)
        row = Text(
            _label(
                "  " * len(parts)
                + f"#{task.get('id', '?')} {task.get('description', '')}",
                label_width,
            ),
            style=color,
        )
        deadline = _deadline(task)
        for index, period in enumerate(periods):
            row.append(_separator(periods, index, zoom), style="dim")
            row.append(_cell(dates, deadline, period), style=f"bold {color}")
        lines.append(row)
    return Group(*lines)


def generate_timeline(constraint, zoom="auto", taskrc=None, scheduling_results=None, config=None):
    start = datetime.today().date()
    end = get_taskwarrior_date(constraint, taskrc=taskrc).date()
    tasks = (
        scheduling_results if scheduling_results is not None else fetch_tasks(taskrc)
    )
    console = Console()
    console.print(
        build_timeline(tasks, start, end, zoom, config=config, columns=console.width)
    )
