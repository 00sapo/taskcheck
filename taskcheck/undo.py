import json
import subprocess
import time
from pathlib import Path

from taskcheck.common import get_task_env


MANAGED_FIELDS = ("scheduled", "completion_date", "scheduling")


def get_task_data_dir(taskrc=None):
    result = subprocess.run(
        ["task", "_get", "rc.data.location"],
        capture_output=True,
        text=True,
        env=get_task_env(taskrc),
        check=False,
    )
    location = result.stdout.strip()
    if not location:
        raise RuntimeError("Taskwarrior data location is not configured")
    return Path(location).expanduser()


def get_undo_dir(taskrc=None):
    return get_task_data_dir(taskrc) / "taskcheck" / "undos"


def create_undo_backup(task_info, n_undos, taskrc=None):
    n_undos = int(n_undos)
    if n_undos <= 0:
        return None

    tasks = []
    for info in task_info.values():
        if not info["scheduling"]:
            continue
        task = info["task"]
        snapshot = {"uuid": task["uuid"]}
        snapshot.update({field: task.get(field) for field in MANAGED_FIELDS})
        tasks.append(snapshot)
    if not tasks:
        return None

    undo_dir = get_undo_dir(taskrc)
    undo_dir.mkdir(parents=True, exist_ok=True)
    backup = undo_dir / f"undo-{time.time_ns()}.json"
    temporary = backup.with_suffix(".tmp")
    temporary.write_text(json.dumps({"tasks": tasks}, indent=2) + "\n")
    temporary.replace(backup)

    backups = sorted(undo_dir.glob("undo-*.json"))
    for expired in backups[:-n_undos]:
        expired.unlink()
    return backup


def restore_latest_backup(taskrc=None):
    undo_dir = get_undo_dir(taskrc)
    backups = sorted(undo_dir.glob("undo-*.json")) if undo_dir.exists() else []
    if not backups:
        print(
            "No undo backup found. Set [scheduler] n_undos to at least 1 and run "
            "taskcheck --schedule before using --undo."
        )
        return False

    backup = backups[-1]
    snapshot = json.loads(backup.read_text())
    env = get_task_env(taskrc)
    for task in snapshot["tasks"]:
        fields = [f"{field}:{task.get(field) or ''}" for field in MANAGED_FIELDS]
        subprocess.run(
            ["task", task["uuid"], "modify", *fields],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )

    backup.unlink()
    print(f"Restored {len(snapshot['tasks'])} task(s) from the latest backup.")
    return True
