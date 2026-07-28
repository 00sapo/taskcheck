import hashlib
import json
from icalendar import Calendar
from datetime import datetime, timedelta
from dateutil.rrule import rruleset, rrulestr
import requests
from pathlib import Path
import appdirs
import zoneinfo

import time

CACHE = Path(appdirs.user_cache_dir("taskcheck"))


def fetch_ical_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def parse_ical_events(ical_text, days_ahead, all_day, tz_name=None, verbose=False):
    cal = Calendar.from_ical(ical_text)
    today = datetime.now().date()
    end_date = today + timedelta(days=days_ahead)

    events = []
    exceptions = set()

    for component in cal.walk():
        if component.name == "VEVENT":
            event_start = component.get("dtstart").dt
            event_end = component.get("dtend").dt
            recurrence_rule = component.get("rrule")
            recurrence_id = component.get("recurrence-id")

            # skip all-day events if not requested
            is_all_day = not hasattr(event_start, "hour") or event_start == event_end
            if is_all_day:
                if not all_day:
                    continue
                else:
                    event_start = datetime(
                        event_start.year,
                        event_start.month,
                        event_start.day,
                    )
                    event_end = datetime(
                        event_end.year,
                        event_end.month,
                        event_end.day,
                    )
                    if event_end <= event_start:
                        event_end = event_start + timedelta(days=1)
            if recurrence_id:
                if end_date >= recurrence_id.dt.date() >= today:
                    # this was an occurrence of a recurring event
                    # but has been moved, let's record the exception that must be removed
                    exceptions.add(recurrence_id.dt.isoformat())

            occurrences = rruleset()
            if recurrence_rule:
                # avoid handling rules that are already ended
                # and don't create events beyond end_date
                until = recurrence_rule.get("UNTIL")
                if until is not None:
                    until = until[0].date()
                    if until < today:
                        continue
                rrule = rrulestr(
                    str(recurrence_rule.to_ical(), "utf-8"),
                    dtstart=event_start,
                )
                occurrences.rrule(rrule)  # type: ignore
                # exceptions to recurring events
                excdates = component.get("exdate")
                if excdates is not None:
                    if isinstance(excdates, list):
                        # concatenate all the .dts into one list
                        excdates = [e for exdate in excdates for e in exdate.dts]
                    else:
                        excdates = excdates.dts
                    for excdate in excdates:
                        if end_date >= excdate.dt.date() >= today:
                            exceptions.add(excdate.dt.isoformat())
            else:
                # if event is not recurring, add it as a single event
                if event_start.date() >= today and event_end.date() <= end_date:
                    occurrences.rdate(event_start)

            for occurrence in occurrences:
                if tz_name is not None:
                    occurrence = occurrence.astimezone(zoneinfo.ZoneInfo(tz_name))
                end = occurrence + (event_end - event_start)
                if occurrence.date() >= today and end.date() <= end_date:
                    events.append(
                        {
                            # "summary": component.get("summary"),
                            "start": occurrence.isoformat(),
                            "end": end.isoformat(),
                        }
                    )
                elif end.date() > end_date:
                    break

    with_exc_len = len(events)
    events = [event for event in events if event["start"] not in exceptions]
    if verbose:
        print(
            f"Removed {with_exc_len - len(events)} events that are exceptions to recurring events"
        )
    events.sort(key=lambda x: x["start"])
    return events


def get_cache_filename(url):
    hash_object = hashlib.sha256(url.encode())
    return CACHE / f"{hash_object.hexdigest()}.json"


def ical_to_dict(
    url, days_ahead=7, all_day=False, expiration=0.25, verbose=False, tz_name=None, force_update=False
):
    CACHE.mkdir(exist_ok=True, parents=True)
    cache_file = CACHE / get_cache_filename(url)
    current_time = time.time()

    # Check if cache file exists and is not expired
    if cache_file.exists() and not force_update:
        cache_mtime = cache_file.stat().st_mtime
        if current_time - cache_mtime < expiration * 3600:
            with open(cache_file, "r") as f:
                events = json.load(f)
            if verbose:
                print("Loaded events from cache")
            return events

    # Fetch and parse iCal data
    ttt = time.time()
    ical_text = fetch_ical_data(url)
    if verbose:
        print("Time taken to fetch ical data: ", time.time() - ttt)
    ttt = time.time()
    events = parse_ical_events(
        ical_text, days_ahead, all_day, tz_name=tz_name, verbose=verbose
    )
    if verbose:
        print("Time taken to parse ical data: ", time.time() - ttt)

    # Save events to cache
    with open(cache_file, "w") as f:
        json.dump(events, f)

    return events
