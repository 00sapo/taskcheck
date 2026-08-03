import json
from pathlib import Path

from taskcheck.undo import get_task_data_dir


def get_dry_run_path(taskrc=None):
    return get_task_data_dir(taskrc) / "taskcheck" / "dry-run.json"


def save_dry_run_results(results, taskrc=None):
    path = get_dry_run_path(taskrc)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2, sort_keys=True))
    return path


def load_dry_run_results(taskrc=None):
    path = get_dry_run_path(taskrc)
    if not path.exists():
        return None
    return json.loads(path.read_text())
