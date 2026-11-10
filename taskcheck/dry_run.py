import json
import subprocess
from pathlib import Path

from taskcheck.undo import get_task_data_dir
from taskcheck.common import get_task_env


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
    results = json.loads(path.read_text())
    if not results:
        return results
    response = subprocess.run(
        ["task", "export"], capture_output=True, text=True,
        env=get_task_env(taskrc),
    )
    current_tasks = {
        task["uuid"]: task for task in json.loads(response.stdout)
    }
    return [
        {**current_tasks.get(task.get("uuid"), {}), **task}
        for task in results
    ]
