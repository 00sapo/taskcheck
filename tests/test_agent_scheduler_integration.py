"""Integration coverage against taskcheck.parallel's day-allocation loop."""
from datetime import datetime, timedelta

import pytest

from taskcheck.parallel import UrgencyCoefficients, allocate_time_for_day


COEFFS = UrgencyCoefficients({"PT2H": 0}, False, 0, 365, 0, 0)


def info(name, *, hours=2, urgency=10, agent=False, weight=None, depends=()):
    t = {"uuid": name, "id": name, "description": name,
         "estimated": "PT2H", "min_block": 2}
    if agent:
        t["tags"] = ["agent"]
        t["agent_weight"] = weight
    if depends:
        t["depends"] = list(depends)
    return {"task": t, "remaining_hours": hours,
            "task_time_map": [2.0, 2.0], "today_used_hours": 0,
            "scheduling": {}, "urgency": urgency,
            "estimated_urgency": 0, "age_urgency": 0, "due_urgency": 0,
            "started": False}


def schedule(tasks, monkeypatch):
    monkeypatch.setattr('taskcheck.parallel.recompute_urgencies', lambda *args, **kwargs: None)
    allocate_time_for_day(tasks, 1, COEFFS, False, 1)
    return (datetime.today().date() + timedelta(days=1)).isoformat()


def test_mixed_allocation_inside_one_calendar_block(monkeypatch):
    tasks = {"a": info("a", agent=True, weight=25),
             "b": info("b", agent=True, weight=35, urgency=9),
             "h": info("h", hours=.8, urgency=8)}
    day = schedule(tasks, monkeypatch)
    assert tasks["a"]["scheduling"] == {day: 2}
    assert tasks["b"]["scheduling"] == {day: 2}
    assert tasks["h"]["scheduling"] == pytest.approx({day: .8})


def test_more_urgent_human_keeps_exclusive_block(monkeypatch):
    tasks = {"h": info("h", urgency=20),
             "a": info("a", agent=True, weight=25, urgency=10)}
    day = schedule(tasks, monkeypatch)
    assert tasks["h"]["scheduling"] == {day: 2}
    assert tasks["a"]["scheduling"] == {}


def test_dependencies_wait_for_next_block(monkeypatch):
    tasks = {"a": info("a", agent=True, weight=25, urgency=20),
             "dependent": info("dependent", hours=.5, urgency=18, depends=("a",)),
             "h": info("h", hours=.5, urgency=15)}
    day = schedule(tasks, monkeypatch)
    assert tasks["dependent"]["scheduling"] == {}
    assert tasks["h"]["scheduling"] == {day: .5}


def test_five_hour_agent_ten_percent_occupies_two_and_half_blocks(monkeypatch):
    # estimated:5h = execution time, NOT supervision time.
    monkeypatch.setattr('taskcheck.parallel.recompute_urgencies', lambda *args, **kwargs: None)
    agent = info('a', hours=5, agent=True, weight=10)
    agent['task']['estimated'] = 'PT5H'
    agent['task_time_map'] = [2.0, 2.0, 2.0, 2.0]
    allocated_days = []
    for offset in range(1, 4):
        allocate_time_for_day({'a': agent}, offset, COEFFS, False, 1)
        day = (datetime.today().date() + timedelta(days=offset)).isoformat()
        allocated_days.append(agent['scheduling'].get(day, 0))
    assert allocated_days == pytest.approx([2, 2, 1])
    assert sum(allocated_days) == pytest.approx(5)
    assert sum(allocated_days) * .10 == pytest.approx(.5)
    assert agent['remaining_hours'] == pytest.approx(0)


def test_five_hour_agent_and_four_hour_human_fit_in_five_calendar_hours(monkeypatch):
    """Regression: estimates are agent wall-time, NOT supervision time."""
    monkeypatch.setattr('taskcheck.parallel.recompute_urgencies', lambda *args, **kwargs: None)
    a = info('a', hours=5, agent=True, weight=10, urgency=20)
    a['task']['estimated'] = 'PT5H'
    h = info('h', hours=4, urgency=10)
    for item in (a, h):
        item['task_time_map'] = [0, 5]
    task_info = {'a': a, 'h': h}
    allocate_time_for_day(task_info, 1, COEFFS, False, 1)
    day = (datetime.today().date() + timedelta(days=1)).isoformat()
    assert a['scheduling'][day] == pytest.approx(5)
    assert h['scheduling'][day] == pytest.approx(4)
    assert a['remaining_hours'] == pytest.approx(0)
    assert h['remaining_hours'] == pytest.approx(0)
    # 5h elapsed, with 5h*10%=0.5h supervision + 4h independent work.
    assert a['scheduling'][day] * .10 + h['scheduling'][day] == pytest.approx(4.5)


def test_initialize_task_info_does_not_share_cached_availability(monkeypatch):
    from taskcheck.parallel import initialize_task_info
    shared = [3., 3.]
    monkeypatch.setattr('taskcheck.parallel.get_long_range_time_map',
                        lambda *args: (shared, 0))
    tasks = [
        {'id': 1, 'uuid': 'a', 'estimated': 'PT2H', 'time_map': 'work',
         'tags': ['agent'], 'agent_weight': 25},
        {'id': 2, 'uuid': 'h', 'estimated': 'PT2H', 'time_map': 'work'},
    ]
    states = initialize_task_info(tasks, {}, 2, COEFFS, [])
    assert states['a']['task_time_map'] is not states['h']['task_time_map']
    assert states['a']['task_time_map'] is not shared
    states['a']['task_time_map'][0] -= 2
    assert states['h']['task_time_map'] == [3., 3.]
    assert shared == [3., 3.]


def test_initialize_task_info_rejects_missing_agent_weight(monkeypatch):
    from taskcheck.parallel import initialize_task_info
    tasks = [{'id': 1, 'uuid': 'a', 'estimated': 'PT2H',
              'time_map': 'work', 'tags': ['agent']}]
    with pytest.raises(ValueError, match='agent_weight'):
        initialize_task_info(tasks, {}, 2, COEFFS, [])


def test_availability_cache_is_scoped_to_horizon_and_time_map():
    """A new schedule must not inherit a stale cached horizon or work profile."""
    from taskcheck.common import get_long_range_time_map, long_range_time_map
    long_range_time_map.clear()
    work = {day: [[9, 17]] for day in
            ('monday', 'tuesday', 'wednesday', 'thursday', 'friday',
             'saturday', 'sunday')}
    try:
        short, _ = get_long_range_time_map({'work': work}, ['work'], 2, [])
        long, _ = get_long_range_time_map({'work': work}, ['work'], 3, [])
        assert len(short) == 2
        assert len(long) == 3
        shorter_hours = {day: [[9, 12]] for day in work}
        changed, _ = get_long_range_time_map(
            {'work': shorter_hours}, ['work'], 3, [])
        assert changed == [3., 3., 3.]
    finally:
        long_range_time_map.clear()


def test_install_registers_agent_weight_uda(monkeypatch):
    from taskcheck import install as install_module
    from unittest.mock import Mock
    apply = Mock()
    monkeypatch.setattr(install_module, 'apply_config', apply)
    answers = iter(('yes', 'no', 'no'))
    monkeypatch.setattr('builtins.input', lambda *args: next(answers))
    install_module.install()
    applied = [call.args for call in apply.call_args_list]
    assert ('uda.agent_weight.type', 'numeric') in applied
    assert ('uda.agent_weight.label', 'Agent Interaction (%)') in applied
