import json
from unittest.mock import patch

from taskcheck.dry_run import load_dry_run_results


def test_old_preview_recovers_missing_attributes_without_changing_schedule(tmp_path):
    path = tmp_path / "dry-run.json"
    cached = [{"uuid": "agent", "scheduling": "2026-11-10 - PT2H"}]
    path.write_text(json.dumps(cached))
    current = [{"uuid": "agent", "agent_weight": 25,
                "scheduling": "2026-11-11 - PT1H"}]
    with patch("taskcheck.dry_run.get_dry_run_path", return_value=path), patch(
        "taskcheck.dry_run.subprocess.run"
    ) as export:
        export.return_value.stdout = json.dumps(current)
        result = load_dry_run_results()
    assert result is not None
    assert result[0]["agent_weight"] == 25
    assert result[0]["scheduling"] == "2026-11-10 - PT2H"
    assert json.loads(path.read_text()) == cached
