from io import StringIO

from rich.console import Console

from taskcheck.report import build_tasks_table, build_unplanned_tasks_table, get_tasks


def test_explicit_columns_replace_defaults_in_order():
    task = {"id": 2, "description": "Agent work", "urgency": 1,
            "tags": ["agent"], "agent_weight": 0.34,
            "scheduling": "2026-11-10 - PT2H"}
    config = {"attributes": ["agent_weight", "description"],
              "attribute_labels": {"agent_weight": "Attention"}}
    rows = get_tasks(config, [task], 2026, 11, 10)
    table = build_tasks_table(config, rows)
    assert [column.header for column in table.columns] == ["Attention", "Description"]
    stream = StringIO()
    Console(file=stream, width=100).print(table)
    assert "0.34" in stream.getvalue()
    assert "Agent work" in stream.getvalue()
    assert "#2" not in stream.getvalue()


def test_unplanned_columns_are_independent_and_empty_means_none():
    config = {"attributes": [], "attributes_unplanned": ["description"]}
    tasks = [{"id": 1, "description": "Unplanned work"}]
    assert build_tasks_table(config, tasks).columns == []
    table = build_unplanned_tasks_table(config, tasks)
    assert [column.header for column in table.columns] == ["Description"]
