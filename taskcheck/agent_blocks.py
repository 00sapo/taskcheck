"""Plan mixed agent/human work inside an ordinary Taskcheck block.

All durations are hours. Agent estimates describe elapsed execution time while
agent_weight is the percentage of that time needing human interaction. A block
consumes its full elapsed duration from the calendar, not the sum of the task
estimates. Internal allocations never create scheduling sub-blocks.
"""

from datetime import datetime
from math import isfinite

from taskcheck.common import hours_to_decimal

_EPSILON = 1e-9


def get_agent_weight(task):
    """Return human-interaction fraction for +agent tasks, else None.

    A tagged task must specify a percentage from 0 to 100. In particular,
    missing weights must not silently imply free, infinite parallelism.
    """
    if "agent" not in (task.get("tags") or []):
        return None
    try:
        weight = float(task["agent_weight"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"Task {task.get('id', task.get('uuid'))}: +agent requires a numeric agent_weight"
        ) from exc
    if not isfinite(weight) or not 0 <= weight <= 100:
        raise ValueError(
            f"Task {task.get('id', task.get('uuid'))}: agent_weight must be between 0 and 100"
        )
    return weight / 100


def _eligible(info, pending, date):
    if any(dep in pending for dep in info["task"].get("depends", [])):
        return False
    wait = info["task"].get("wait")
    if wait and date < datetime.strptime(wait, "%Y%m%dT%H%M%SZ").date():
        return False
    return True


def _max_allocation(info, day_offset, block_hours):
    return min(
        float(info["remaining_hours"]),
        float(info["task_time_map"][day_offset]),
        block_hours,
    )


def allocate_agent_block(
    tasks_remaining, sorted_task_ids, day_offset, day_remaining_hours, date, anchor_uuid
):
    """Allocate one block anchored by an eligible agent task.

    Returns (elapsed_hours, {uuid: allocated_task_hours}), and mutates the
    selected task states in-place. None of the individual allocations is a
    calendar sub-block. All agents run within the same elapsed block; human
    work consumes interaction time left unused by the agents.

    Tasks which depend on anything pending *at block start* cannot join this
    same block, even if that prerequisite finishes within it.
    """
    anchor = tasks_remaining[anchor_uuid]
    if get_agent_weight(anchor["task"]) is None:
        return 0, {}
    pending = set(tasks_remaining)
    if not _eligible(anchor, pending, date):
        return 0, {}
    block_hours = min(
        day_remaining_hours,
        hours_to_decimal(float(anchor["task"].get("min_block", 2))),
    )
    if block_hours <= _EPSILON:
        return 0, {}

    allocations = {}
    human_budget = block_hours
    agent_order = [anchor_uuid] + [uuid for uuid in sorted_task_ids if uuid != anchor_uuid]
    for uuid in agent_order:
        info = tasks_remaining.get(uuid)
        if info is None:
            continue
        weight = get_agent_weight(info["task"])
        if weight is None or not _eligible(info, pending, date):
            continue
        agent_cap = min(
            block_hours,
            hours_to_decimal(float(info["task"].get("min_block", 2))),
        )
        duration = _max_allocation(info, day_offset, agent_cap)
        if weight > 0:
            duration = min(duration, max(human_budget, 0) / weight)
        if duration <= _EPSILON:
            continue
        allocations[uuid] = duration
        human_budget = max(0, human_budget - weight * duration)

    # The anchor must have actual execution time; a zero-length block is invalid.
    if anchor_uuid not in allocations:
        return 0, {}

    for uuid in sorted_task_ids:
        info = tasks_remaining.get(uuid)
        if info is None or get_agent_weight(info["task"]) is not None:
            continue
        if not _eligible(info, pending, date):
            continue
        # Deliberately allow sub-min_block *allocations*, but only in a mixed
        # block. Standalone human scheduling stays in the legacy path.
        # Honor task-specific chunk caps while allowing allocations *smaller*
        # than that cap only within this mixed block.
        human_cap = min(
            human_budget, hours_to_decimal(float(info["task"].get("min_block", 2)))
        )
        duration = _max_allocation(info, day_offset, human_cap)
        if duration <= _EPSILON:
            continue
        allocations[uuid] = duration
        human_budget = max(0, human_budget - duration)
        if human_budget <= _EPSILON:
            break

    # Charge only elapsed calendar time actually needed. Otherwise a short
    # agent finishing alone would artificially consume a whole min_block.
    # Interaction and human work must fit inside this elapsed interval, while
    # all agent executions may overlap.
    interaction_hours = sum(
        duration * get_agent_weight(tasks_remaining[uuid]["task"])
        if get_agent_weight(tasks_remaining[uuid]["task"]) is not None
        else duration
        for uuid, duration in allocations.items()
    )
    elapsed_hours = max(
        interaction_hours,
        *(
            duration
            for uuid, duration in allocations.items()
            if get_agent_weight(tasks_remaining[uuid]["task"]) is not None
        ),
    )

    date_str = date.isoformat()
    for uuid, duration in allocations.items():
        info = tasks_remaining[uuid]
        if not info["scheduling"]:
            info["started"] = True
        info["remaining_hours"] = max(0, info["remaining_hours"] - duration)
        # Cached time-map lists may be shared by different tasks; the mutable
        # per-task remaining availability must not alias another task.
        info["task_time_map"] = list(info["task_time_map"])
        info["task_time_map"][day_offset] = max(
            0, info["task_time_map"][day_offset] - duration
        )
        info["scheduling"][date_str] = info["scheduling"].get(date_str, 0) + duration
    return elapsed_hours, allocations
