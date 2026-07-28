import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
import appdirs
from rich.console import Console

from taskcheck.ical import ical_to_dict

console = Console()

config_dir = Path(appdirs.user_config_dir("task"))

# Taskwarrior status to avoid
AVOID_STATUS = ["completed", "deleted", "recurring"]

long_range_time_map = {}


def get_task_env(taskrc=None):
    import os
    env = os.environ.copy()
    if taskrc:
        env['TASKRC'] = taskrc
        env['TASKDATA'] = taskrc
    return env


# Get tasks from Taskwarrior and sort by urgency
def get_tasks(taskrc=None):
    env = get_task_env(taskrc)
    result = subprocess.run(["task", "export"], capture_output=True, text=True, env=env)
    tasks = json.loads(result.stdout)
    return sorted(
        (task for task in tasks if "estimated" in task),
        key=lambda t: -t.get("urgency", 0),
    )


def hours_to_decimal(hour):
    return int(hour) + (hour - int(hour)) * 100 / 60


def hours_to_time(hour):
    hours = int(hour)
    minutes = int((hour - hours) * 100)
    return datetime.strptime(f"{hours}:{minutes}", "%H:%M").time()


def time_to_decimal(time):
    # round to 2 digits after the point
    return time.hour + time.minute / 60


def get_available_hours(time_map, date, calendars, verbose=False):
    day_of_week = date.strftime("%A").lower()
    schedule = time_map.get(day_of_week, [])
    available_hours = sum(
        hours_to_decimal(end) - hours_to_decimal(start) for start, end in schedule
    )

    blocked_hours = 0
    for schedule_start, schedule_end in schedule:
        # schedule_start and schedule_end are numbers, actually
        # so let's convert them to datetime.time objects
        schedule_start = hours_to_time(schedule_start)
        schedule_end = hours_to_time(schedule_end)
        schedule_blocked_hours = 0
        for calendar in calendars:
            for event in calendar:
                # we use str to make object serializable as jsons
                if isinstance(event["start"], str):
                    event["start"] = datetime.fromisoformat(event["start"])
                if isinstance(event["end"], str):
                    event["end"] = datetime.fromisoformat(event["end"])

                if event["start"].date() > date:
                    break
                elif event["end"].date() < date:
                    continue

                # check if the event overlaps with one of the working hours
                event_start = event["start"].time()
                event_end = event["end"].time()
                if event["start"].date() < date:
                    event_start = datetime(date.year, date.month, date.day, 0, 0).time()
                if event["end"].date() > date:
                    event_end = datetime(date.year, date.month, date.day, 23, 59).time()

                if event_start < schedule_end and event_end > schedule_start:
                    schedule_blocked_hours += time_to_decimal(
                        min(schedule_end, event_end)
                    ) - time_to_decimal(max(schedule_start, event_start))
        if verbose and schedule_blocked_hours > 0:
            print(
                f"Blocked hours on {date} between {schedule_start} and {schedule_end}: {schedule_blocked_hours}"
            )
        blocked_hours += schedule_blocked_hours
    available_hours -= blocked_hours
    return available_hours


def pdth_to_hours(duration_str):
    # string format is P#DT#H
    # with D and H optional
    duration_str = duration_str[1:]  # Remove leading "P"
    days, hours, minutes = 0, 0, 0
    if "D" in duration_str:
        days, duration_str = duration_str.split("D")
        days = int(days)
    if "H" in duration_str:
        if "T" in duration_str:
            hours = int(duration_str.split("T")[1].split("H")[0])
        else:
            hours = int(duration_str.split("H")[0])
    if "M" in duration_str:
        if "H" in duration_str:
            minutes = int(duration_str.split("H")[1].split("M")[0])
        else:
            if "T" in duration_str:
                minutes = int(duration_str.split("T")[1].split("M")[0])
            else:
                minutes = int(duration_str.split("M")[0])
    return days * 24 + hours + minutes / 60


def hours_to_pdth(hours):
    days_ = hours / 24
    hours_ = hours % 24
    minutes_ = int(round((hours_ - int(hours_)) * 60))
    days_ = int(days_)
    hours_ = int(hours_)
    minutes_ = int(minutes_)
    ret = "P"
    if days_ == 0:
        ret += "T"
    else:
        ret += f"{days_}DT"
    if hours_ > 0:
        ret += f"{hours_}H"
    if minutes_ > 0:
        ret += f"{minutes_}M"
    if ret == "PT":
        print("Warning: hours_to_pdth() returned 'PT' for hours = ", hours)
    return ret


def get_long_range_time_map(
    time_maps, time_map_names, days_ahead, calendars, verbose=False
):
    key = ",".join(time_map_names)
    if key in long_range_time_map:
        task_time_map = long_range_time_map[key]
    else:
        if verbose:
            print(f"Calculating long range time map for {key}")
        task_time_map = []
        for d in range(days_ahead):
            date = datetime.today().date() + timedelta(days=d)
            daily_hours = 0
            for time_map_name in time_map_names:
                if time_map_name not in time_maps:
                    raise ValueError(f"Time map '{time_map_name}' does not exist.")
                time_map = time_maps[time_map_name]
                daily_hours += get_available_hours(time_map, date, calendars)
            task_time_map.append(daily_hours)
        long_range_time_map[key] = task_time_map

    today_time = time_to_decimal(datetime.now().time())
    today_weekday = datetime.today().strftime("%A").lower()
    today_used_hours = 0
    # compare with the time_maps of today
    for time_map_name in time_map_names:
        time_map = time_maps[time_map_name].get(today_weekday)
        if time_map:
            for schedule_start, schedule_end in time_map:
                schedule_start = hours_to_decimal(schedule_start)
                schedule_end = hours_to_decimal(schedule_end)
                if schedule_start <= today_time <= schedule_end:
                    today_used_hours += today_time - schedule_start
                    break
                elif today_time > schedule_end:
                    today_used_hours += schedule_end - schedule_start
    return task_time_map, today_used_hours


def mark_end_date(
    due_date, end_date, start_date, scheduling_note, id, description=None, taskrc=None
):
    start_end_fields = [f"scheduled:{start_date}", f"completion_date:{end_date}"]
    env = get_task_env(taskrc)

    subprocess.run(
        [
            "task",
            str(id),
            "modify",
            *start_end_fields,
            f"scheduling:{scheduling_note}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    if due_date is not None and end_date > due_date:
        # print in bold red using ANSI escape codes
        description = "('" + description + "')" if description is not None else ""
        print(f"\033[1;31mTask {id} {description} may not be completed on time\033[0m")


def get_calendars(config, verbose=False, force_update=False):
    calendars = []
    for calname in config["calendars"]:
        calendar = config["calendars"][calname]
        calendar = ical_to_dict(
            calendar["url"],
            config["scheduler"]["days_ahead"],
            all_day=calendar["event_all_day_is_blocking"],
            expiration=calendar["expiration"],
            verbose=verbose,
            tz_name=calendar.get("timezone"),
            force_update=force_update,
        )
        calendar.sort(key=lambda e: e["start"])
        calendars.append(calendar)
    if verbose:
        print(f"Loaded {len(calendars)} calendars")
    return calendars
