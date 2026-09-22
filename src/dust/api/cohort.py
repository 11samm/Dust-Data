from __future__ import annotations

import random

from dust.config import COHORT_SIZE, DEPARTMENTS


def allocate_slots(totals: dict[str, int], target: int = COHORT_SIZE) -> dict[str, int]:
    """Proportional stratified allocation with minimum 1 per non-empty department."""
    active = {d: t for d, t in totals.items() if t > 0}
    if not active:
        return {}

    if len(active) > target:
        # More departments than slots: take target largest departments with 1 each
        ordered = sorted(active.items(), key=lambda x: (-x[1], x[0]))[:target]
        return {d: 1 for d, _ in ordered}

    slots = {d: 1 for d in active}
    remaining = target - len(active)
    total_count = sum(active.values())
    if remaining <= 0:
        return slots

    raw_extra = {d: remaining * active[d] / total_count for d in active}
    floor_extra = {d: int(raw_extra[d]) for d in active}
    for d in active:
        slots[d] += floor_extra[d]

    assigned = sum(floor_extra.values())
    leftover = remaining - assigned
    if leftover > 0:
        remainders = sorted(
            ((raw_extra[d] - floor_extra[d], d) for d in active),
            key=lambda x: (-x[0], x[1]),
        )
        for _, dept in remainders[:leftover]:
            slots[dept] += 1

    # Trim if rounding pushed over target
    while sum(slots.values()) > target:
        dept = max(slots.items(), key=lambda x: (x[1], x[0]))[0]
        if slots[dept] > 1:
            slots[dept] -= 1
        else:
            break

    return slots


def probe_department_totals(client, departments: list[str] | None = None) -> dict[str, int]:
    departments = departments or DEPARTMENTS
    totals: dict[str, int] = {}
    for dept in departments:
        totals[dept] = client.department_total(dept)
    return totals


def _random_start(total: int, count: int, rng: random.Random) -> int:
    return rng.randint(0, max(0, total - count))


def fetch_stratified_cohort(
    client,
    target: int = COHORT_SIZE,
    *,
    rng: random.Random | None = None,
) -> tuple[list[dict], list[str]]:
    rng = rng or random.SystemRandom()
    totals = probe_department_totals(client)
    allocation = allocate_slots(totals, target)
    records: list[dict] = []
    errors: list[str] = []
    seen: set[int] = set()

    for dept, count in sorted(allocation.items()):
        try:
            start = _random_start(totals[dept], count, rng)
            batch = client.fetch_department_records(dept, count, skip=start)
        except Exception:
            errors.append(dept)
            continue
        for item in batch:
            art_id = item.get("id")
            if art_id in seen:
                continue
            seen.add(art_id)
            records.append(item)

    return records, errors


def fetch_filtered_cohort(
    client,
    *,
    mode: str,
    department: str | None = None,
    type_: str | None = None,
    limit: int = COHORT_SIZE,
) -> list[dict]:
    rng = random.SystemRandom()
    if mode == "department" and department:
        total = client.department_total(department)
        return client.fetch_department_records(
            department,
            limit,
            skip=_random_start(total, limit, rng),
        )
    if mode == "type" and type_:
        total = client.type_total(type_)
        return client.fetch_type_records(
            type_,
            limit,
            skip=_random_start(total, limit, rng),
        )
    records, _errors = fetch_stratified_cohort(client, limit, rng=rng)
    return records
