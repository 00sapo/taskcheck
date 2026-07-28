import json
import warnings
from pathlib import Path
from urllib.parse import urlparse

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from taskcheck.common import config_dir, get_task_env

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def get_google_data_dir(taskrc=None):
    env = get_task_env(taskrc)
    base = Path(env.get("TASKDATA", config_dir))
    return base / "google"


def get_client_secrets_path(taskrc=None):
    repo_secret = Path.cwd() / "client_secret.json"
    if repo_secret.exists():
        return repo_secret
    return get_google_data_dir(taskrc) / "client_secret.json"


def get_token_path(account_id, taskrc=None):
    return get_google_data_dir(taskrc) / f"{account_id}.token.json"


def _safe_account_id(email):
    return email.replace("@", "_").replace(".", "_")


def load_credentials(taskrc=None):
    secrets_path = get_client_secrets_path(taskrc)
    if not secrets_path.exists():
        raise FileNotFoundError(f"Missing Google OAuth client secrets: {secrets_path}")

    token_dir = get_google_data_dir(taskrc)
    token_dir.mkdir(parents=True, exist_ok=True)
    token_path = token_dir / "current.token.json"
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r'^Scope has changed from .*')
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())
    return creds


def get_google_user_email(credentials):
    response = requests.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["email"], payload.get("name", payload["email"])


def list_calendars(credentials):
    service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
    result = service.calendarList().list().execute()
    return result.get("items", [])


def select_from_list(items, title_key="summary"):
    for idx, item in enumerate(items, start=1):
        print(f"{idx}. {item.get(title_key, item.get('id'))}")
    while True:
        choice = input("Select one calendar: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(items):
            return items[int(choice) - 1]
        print("Invalid selection")


def render_calendar_config(account_id, calendar, taskrc=None):
    token_path = get_token_path(account_id, taskrc)
    return f'''[calendars."{account_id}.{calendar["id"]}"]
url = "google://{calendar["id"]}"
provider = "google"
account = "{account_id}"
calendar_id = "{calendar["id"]}"
token_path = "{token_path}"
event_all_day_is_blocking = true
expiration = 0.25
'''


def add_google_calendar(taskrc=None):
    credentials = load_credentials(taskrc)
    email, name = get_google_user_email(credentials)
    account_id = _safe_account_id(email)
    token_path = get_token_path(account_id, taskrc)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json())

    calendars = list_calendars(credentials)
    if not calendars:
        raise RuntimeError("No Google calendars found for this account")
    calendar = select_from_list(calendars)
    print(render_calendar_config(account_id, calendar, taskrc=taskrc))
    return {
        "account_id": account_id,
        "email": email,
        "name": name,
        "calendar": calendar,
        "token_path": str(token_path),
    }
