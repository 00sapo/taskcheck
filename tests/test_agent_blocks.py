from datetime import date, timedelta

import pytest

from taskcheck.agent_blocks import allocate_agent_block, get_agent_weight

TODAY = date.today()


def task(name, *, agent=False, weight=None, hours=2, urgency=10, depends=(), wait=None, daily=8):
    record = {"uuid": name, "id": name, "estimated": "PT2H", "min_block": 2}
    if agent:
        record["tags"] = ["agent"]
    if weight is not None:
        record["agent_weight"] = weight
    if depends:
        record["depends"] = list(depends)
    if wait:
        record["wait"] = wait
    return {"task": record, "remaining_hours": hours, "task_time_map": [daily],
            "scheduling": {}, "started": False, "urgency": urgency}


def run(items, order=None, block=2):
    ordered = order or sorted(items, key=lambda name: -items[name]["urgency"])
    return allocate_agent_block(items, ordered, 0, block, TODAY, ordered[0])


def test_mixed_two_agents_and_short_human_tasks():
    items = {
        "a": task("a", agent=True, weight=25),
        "b": task("b", agent=True, weight=35),
        "h1": task("h1", hours=.5),
        "h2": task("h2", hours=.5),
    }
    elapsed, selected = run(items, ["a", "b", "h1", "h2"])
    assert elapsed == 2
    assert selected == pytest.approx({"a": 2, "b": 2, "h1": .5, "h2": .3})
    assert items["h1"]["remaining_hours"] == pytest.approx(0)
    assert items["h2"]["remaining_hours"] == pytest.approx(.2)
    assert all(set(info["scheduling"]) == {TODAY.isoformat()} for info in items.values())


def test_short_agent_duration_consumes_only_actual_interaction():
    items = {"a": task("a", agent=True, weight=25, hours=1),
             "h": task("h", hours=2)}
    elapsed, allocation = run(items, ["a", "h"])
    assert elapsed == 2
    assert allocation == pytest.approx({"a": 1, "h": 1.75})


def test_full_weight_agent_excludes_human():
    items = {"a": task("a", agent=True, weight=100),
             "h": task("h", hours=2)}
    _, selected = run(items, ["a", "h"])
    assert selected == {"a": 2}
    assert items["h"]["remaining_hours"] == 2


def test_dependencies_cannot_execute_with_agent_in_same_block():
    items = {"a": task("a", agent=True, weight=25),
             "h": task("h", hours=1, depends=["a"]),
             "other": task("other", hours=1)}
    _, selected = run(items, ["a", "h", "other"])
    assert "h" not in selected
    assert selected["other"] == 1


def test_waiting_agent_excluded_even_when_urgent():
    tomorrow = (TODAY + timedelta(days=1)).strftime("%Y%m%dT%H%M%SZ")
    items = {"a": task("a", agent=True, weight=25),
             "b": task("b", agent=True, weight=25, wait=tomorrow),
             "h": task("h", hours=2)}
    _, selected = run(items, ["a", "b", "h"])
    assert selected == pytest.approx({"a": 2, "h": 1.5})


def test_daily_availability_limits_agent_and_human():
    items = {"a": task("a", agent=True, weight=50, daily=.5),
             "h": task("h", hours=2, daily=.75)}
    elapsed, selected = run(items, ["a", "h"])
    assert elapsed == pytest.approx(1)
    assert selected == pytest.approx({"a": .5, "h": .75})


def test_agent_capacity_limits_multiple_agents():
    items = {"a": task("a", agent=True, weight=80),
             "b": task("b", agent=True, weight=40)}
    _, selected = run(items, ["a", "b"])
    assert selected == pytest.approx({"a": 2, "b": 1})


@pytest.mark.parametrize("bad", [None, -1, 101, "bad", float("nan")])
def test_invalid_weight_is_rejected(bad):
    t = task("a", agent=True, weight=bad)["task"]
    with pytest.raises(ValueError, match="agent_weight"):
        get_agent_weight(t)


def test_non_agent_does_not_require_weight():
    assert get_agent_weight(task("h")["task"]) is None


def test_no_real_subblocks_appear_in_scheduling():
    items = {"a": task("a", agent=True, weight=25), "h": task("h", hours=.5)}
    _, _ = run(items, ["a", "h"])
    assert items["a"]["scheduling"] == {TODAY.isoformat(): 2}
    assert items["h"]["scheduling"] == {TODAY.isoformat(): .5}


def test_short_lone_agent_does_not_reserve_unused_calendar_time():
    items = {"a": task("a", agent=True, weight=25, hours=1)}
    elapsed, selected = run(items, ["a"])
    assert selected == {"a": 1}
    assert elapsed == pytest.approx(1)


def test_mixed_block_elapsed_reflects_agents_and_supervision_time():
    items = {"a": task("a", agent=True, weight=25, hours=1),
             "h": task("h", hours=1)}
    elapsed, selected = run(items, ["a", "h"])
    assert selected == pytest.approx({"a": 1, "h": 1})
    assert elapsed == pytest.approx(1.25)


def test_one_minute_human_task_is_valid_inside_mixed_block():
    # min_block is a bound on *outer* chunks; it does not apply to human
    # allocations inside a mixed block.
    items = {"a": task("a", agent=True, weight=10, hours=2),
             "h": task("h", hours=1 / 60)}
    elapsed, selected = run(items, ["a", "h"])
    assert elapsed == pytest.approx(2)
    assert selected["h"] == pytest.approx(1 / 60)
    assert items["h"]["remaining_hours"] == pytest.approx(0)


def test_one_minute_agent_can_anchor_mixed_block():
    items = {"a": task("a", agent=True, weight=10, hours=1 / 60),
             "h": task("h", hours=.5)}
    elapsed, selected = run(items, ["a", "h"])
    assert selected == pytest.approx({"a": 1 / 60, "h": .5})
    assert elapsed == pytest.approx(.5 + 1 / 600)


def test_cached_time_map_is_not_mutated_across_tasks():
    # get_long_range_time_map caches its list by name in the upstream module.
    # An independent per-task daily cap is required: a task's execution must
    # not eat another task's cap just because they share the same profile.
    items = {"a": task("a", agent=True, weight=10, hours=1),
             "h": task("h", hours=.5)}
    original_shared_map = [2.0]
    items["a"]["task_time_map"] = original_shared_map
    items["h"]["task_time_map"] = original_shared_map
    elapsed, selected = run(items, ["a", "h"])
    assert selected == pytest.approx({"a": 1, "h": .5})
    assert elapsed == pytest.approx(1)
    assert items["a"]["task_time_map"] == pytest.approx([1])
    assert items["h"]["task_time_map"] == pytest.approx([1.5])
    assert original_shared_map == [2.0]


def test_many_mixed_blocks_respect_elapsed_and_human_budget():
    import random
    rng = random.Random(765421)
    for _ in range(500):
        weights = [rng.uniform(0, 100) for _ in range(rng.randint(1, 6))]
        items = {
            f"a{i}": task(f"a{i}", agent=True, weight=w,
                         hours=rng.uniform(.01, 4), daily=rng.uniform(.1, 3))
            for i, w in enumerate(weights)
        }
        for j in range(rng.randint(0, 5)):
            items[f"h{j}"] = task(f"h{j}", hours=rng.uniform(.01, 4),
                                 daily=rng.uniform(.1, 3))
        originals = {name: data['remaining_hours'] for name, data in items.items()}
        elapsed, selected = run(items, list(items))
        assert 0 < elapsed <= 2 + 1e-8
        interaction = sum(selected.get(name, 0) * (get_agent_weight(info['task']) or 0)
                          if 'agent' in info['task'].get('tags', [])
                          else selected.get(name, 0)
                          for name, info in items.items())
        assert interaction <= elapsed + 1e-8
        for name, allocated in selected.items():
            assert allocated <= originals[name] + 1e-8
            assert items[name]['remaining_hours'] >= -1e-8
            if get_agent_weight(items[name]['task']) is not None:
                assert allocated <= elapsed + 1e-8


def test_human_custom_chunk_limit_is_respected_inside_mixed_block():
    items = {"a": task("a", agent=True, weight=10, hours=2),
             "h": task("h", hours=3)}
    items['h']['task']['min_block'] = 0.3  # Original hh.mm convention: 30 minutes.
    elapsed, selected = run(items, ['a', 'h'])
    assert elapsed == pytest.approx(2)
    assert selected['h'] == pytest.approx(.5)
