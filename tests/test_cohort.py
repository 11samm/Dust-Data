import random

from dust.api.cohort import _random_start, allocate_slots, fetch_stratified_cohort


def test_allocation_sums_to_target():
    totals = {"Prints": 8000, "Photography": 2000, "Textiles": 500}
    slots = allocate_slots(totals, target=10)
    assert sum(slots.values()) == 10
    assert slots["Prints"] >= slots["Photography"] >= 1
    assert all(slots[d] >= 1 for d in totals)


def test_allocation_many_departments_minimum_one():
    totals = {f"Dept{i}": i + 1 for i in range(25)}
    slots = allocate_slots(totals, target=1000)
    assert sum(slots.values()) == 1000
    assert len(slots) == 25
    assert min(slots.values()) >= 1


def test_allocation_two_department_example():
    totals = {"Prints": 8000, "Photography": 2000}
    slots = allocate_slots(totals, target=10)
    assert slots["Prints"] == 7
    assert slots["Photography"] == 3


def test_random_start_stays_inside_available_records():
    rng = random.Random(7)
    starts = {_random_start(100, 10, rng) for _ in range(20)}
    assert len(starts) > 1
    assert min(starts) >= 0
    assert max(starts) <= 90
    assert _random_start(5, 10, rng) == 0


def test_stratified_fetch_uses_randomized_department_offsets():
    class FakeClient:
        def __init__(self):
            self.skips = []

        def department_total(self, department):
            return 100

        def fetch_department_records(self, department, slots, *, skip=0):
            self.skips.append(skip)
            return [{"id": skip + i} for i in range(slots)]

    client = FakeClient()
    records, errors = fetch_stratified_cohort(
        client,
        target=20,
        rng=random.Random(11),
    )

    assert not errors
    assert records
    assert any(skip > 0 for skip in client.skips)
