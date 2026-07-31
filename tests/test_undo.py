import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from taskcheck.undo import create_undo_backup, restore_latest_backup


def task_info(scheduled=None, completion_date=None, scheduling=None):
    task = {"uuid": "task-uuid", "id": 1}
    if scheduled is not None:
        task["scheduled"] = scheduled
    if completion_date is not None:
        task["completion_date"] = completion_date
    if scheduling is not None:
        task["scheduling"] = scheduling
    return {"task-uuid": {"task": task, "scheduling": {"2025-01-02": 2.0}}}


def test_create_backup_saves_managed_fields_and_keeps_only_latest(tmp_path):
    with patch("taskcheck.undo.get_task_data_dir", return_value=tmp_path):
        first = create_undo_backup(
            task_info("20250101T000000Z", "20250102T000000Z", "old"), 1
        )
        second = create_undo_backup(task_info(), 1)

    backups = list((tmp_path / "taskcheck" / "undos").glob("*.json"))
    assert backups == [second]
    assert not first.exists()
    assert json.loads(second.read_text())["tasks"] == [
        {
            "uuid": "task-uuid",
            "scheduled": None,
            "completion_date": None,
            "scheduling": None,
        }
    ]


def test_create_backup_skips_tasks_without_scheduling_and_disabled_retention(tmp_path):
    info = task_info()
    info["task-uuid"]["scheduling"] = {}

    with patch("taskcheck.undo.get_task_data_dir", return_value=tmp_path):
        assert create_undo_backup(info, 1) is None
        assert create_undo_backup(task_info(), 0) is None

    assert not (tmp_path / "taskcheck" / "undos").exists()


def test_restore_latest_backup_restores_fields_and_consumes_file(tmp_path):
    backup_dir = tmp_path / "taskcheck" / "undos"
    backup_dir.mkdir(parents=True)
    older = backup_dir / "undo-1000000000000000000.json"
    older.write_text(json.dumps({"tasks": [{"uuid": "older-task"}]}))
    backup = backup_dir / "undo-2000000000000000000.json"
    backup.write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "uuid": "task-uuid",
                        "scheduled": "20250101T000000Z",
                        "completion_date": None,
                        "scheduling": "old schedule",
                    }
                ]
            }
        )
    )

    with patch("taskcheck.undo.get_task_data_dir", return_value=tmp_path), patch(
        "taskcheck.undo.subprocess.run"
    ) as mock_run:
        assert restore_latest_backup(taskrc="/custom/task") is True

    command = mock_run.call_args.args[0]
    kwargs = mock_run.call_args.kwargs
    assert command == [
        "task",
        "task-uuid",
        "modify",
        "scheduled:20250101T000000Z",
        "completion_date:",
        "scheduling:old schedule",
    ]
    assert kwargs["env"]["TASKRC"] == "/custom/task"
    assert kwargs["env"]["TASKDATA"] == "/custom/task"
    assert kwargs["check"] is True
    assert not backup.exists()
    assert older.exists()


def test_restore_without_backup_tells_user_to_enable_n_undos(tmp_path, capsys):
    with patch("taskcheck.undo.get_task_data_dir", return_value=tmp_path):
        assert restore_latest_backup() is False

    assert "n_undos" in capsys.readouterr().out


def test_failed_restore_keeps_backup(tmp_path):
    backup_dir = tmp_path / "taskcheck" / "undos"
    backup_dir.mkdir(parents=True)
    backup = backup_dir / "undo-1.json"
    backup.write_text(json.dumps({"tasks": [{"uuid": "task-uuid"}]}))

    with patch("taskcheck.undo.get_task_data_dir", return_value=tmp_path), patch(
        "taskcheck.undo.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, ["task"]),
    ), pytest.raises(subprocess.CalledProcessError):
        restore_latest_backup()

    assert backup.exists()


def test_get_task_data_dir_uses_taskwarrior_configuration():
    result = Mock(stdout="/data/tasks\n")
    with patch("taskcheck.undo.subprocess.run", return_value=result) as mock_run:
        from taskcheck.undo import get_task_data_dir

        assert get_task_data_dir("/custom/task") == Path("/data/tasks")

    command = mock_run.call_args.args[0]
    kwargs = mock_run.call_args.kwargs
    assert command == ["task", "_get", "rc.data.location"]
    assert kwargs["env"]["TASKRC"] == "/custom/task"
    assert kwargs["env"]["TASKDATA"] == "/custom/task"
    assert kwargs["check"] is False
