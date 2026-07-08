"""Tests for the Scheduler sorting & filtering methods.

Covers:
  - sort_by_time(tasks)          -> chronological, unscheduled last
  - filter_by_completion(tasks, completed)
  - filter_by_pet_name(owner, pet_name)
and the new Task.start_time field + validation.

Run from the repo root with:  python -m pytest tests/test_sort_filter.py -q
"""

import pytest

from pawpal_system import Owner, Pet, Task, Scheduler


@pytest.fixture
def scheduler():
    return Scheduler()


@pytest.fixture
def owner():
    """Owner 'Priya' with two pets; tasks span times, completion, and priority."""
    o = Owner("Priya")
    rex = Pet("dog1", "Rex", "dog", age=4)
    cat = Pet("cat1", "Whiskers", "cat", age=2)
    o.add_pet(rex)
    o.add_pet(cat)
    rex.add_task(Task("t1", "Evening walk", 30, priority="high", start_time="18:00"))
    rex.add_task(Task("t2", "Morning walk", 30, priority="high", start_time="09:30"))
    rex.add_task(Task("t3", "Vet call", 15, priority="medium"))  # no start_time
    cat.add_task(Task("t4", "Feed", 10, priority="high", start_time="08:00"))
    cat.add_task(Task("t5", "Laser play", 20, priority="low", start_time="12:15"))
    return o


# --- Task.start_time field + validation ------------------------------------

class TestStartTimeField:
    def test_defaults_to_none(self):
        assert Task("x", "T", 10).start_time is None

    def test_accepts_valid_time(self):
        assert Task("x", "T", 10, start_time="09:30").start_time == "09:30"

    def test_accepts_boundaries(self):
        assert Task("x", "T", 10, start_time="00:00").start_time == "00:00"
        assert Task("x", "T", 10, start_time="23:59").start_time == "23:59"

    @pytest.mark.parametrize("bad", ["9:30", "24:00", "12:60", "0930", "noon", "12:", ":30"])
    def test_rejects_malformed(self, bad):
        with pytest.raises(ValueError):
            Task("x", "T", 10, start_time=bad)


# --- sort_by_time ----------------------------------------------------------

class TestSortByTime:
    def test_orders_chronologically(self, scheduler):
        """08:00 < 09:30 < 18:00 by clock, proven via string sort."""
        tasks = [
            Task("c", "C", 10, start_time="18:00"),
            Task("a", "A", 10, start_time="08:00"),
            Task("b", "B", 10, start_time="09:30"),
        ]
        assert [t.id for t in scheduler.sort_by_time(tasks)] == ["a", "b", "c"]

    def test_none_start_times_go_last(self, scheduler):
        """Unscheduled tasks must not vanish or crash the sort — they trail."""
        tasks = [
            Task("none", "N", 10),                       # None
            Task("early", "E", 10, start_time="07:00"),
        ]
        assert [t.id for t in scheduler.sort_by_time(tasks)] == ["early", "none"]

    def test_all_none_keeps_input_order(self, scheduler):
        """Stable sort: with no times, nothing reorders."""
        tasks = [Task("a", "A", 10), Task("b", "B", 10)]
        assert [t.id for t in scheduler.sort_by_time(tasks)] == ["a", "b"]

    def test_empty_list(self, scheduler):
        assert scheduler.sort_by_time([]) == []

    def test_does_not_mutate_input(self, scheduler):
        tasks = [Task("b", "B", 10, start_time="10:00"), Task("a", "A", 10, start_time="08:00")]
        snapshot = list(tasks)
        scheduler.sort_by_time(tasks)
        assert tasks == snapshot  # original order untouched


# --- filter_by_completion --------------------------------------------------

class TestFilterByCompletion:
    def test_keeps_only_incomplete(self, scheduler):
        done = Task("d", "Done", 10)
        done.mark_complete()
        todo = Task("t", "Todo", 10)
        result = scheduler.filter_by_completion([done, todo], completed=False)
        assert [t.id for t in result] == ["t"]

    def test_keeps_only_complete(self, scheduler):
        done = Task("d", "Done", 10)
        done.mark_complete()
        todo = Task("t", "Todo", 10)
        result = scheduler.filter_by_completion([done, todo], completed=True)
        assert [t.id for t in result] == ["d"]

    def test_empty_list(self, scheduler):
        assert scheduler.filter_by_completion([], completed=True) == []

    def test_preserves_order(self, scheduler):
        a, b, c = Task("a", "A", 10), Task("b", "B", 10), Task("c", "C", 10)
        result = scheduler.filter_by_completion([a, b, c], completed=False)
        assert [t.id for t in result] == ["a", "b", "c"]


# --- filter_by_pet_name ----------------------------------------------------

class TestFilterByPetName:
    def test_returns_that_pets_tasks(self, scheduler, owner):
        result = scheduler.filter_by_pet_name(owner, "Rex")
        assert {t.id for t in result} == {"t1", "t2", "t3"}

    def test_case_insensitive(self, scheduler, owner):
        assert len(scheduler.filter_by_pet_name(owner, "rex")) == 3
        assert len(scheduler.filter_by_pet_name(owner, "REX")) == 3

    def test_unknown_pet_returns_empty(self, scheduler, owner):
        assert scheduler.filter_by_pet_name(owner, "Ghost") == []

    def test_owner_with_no_pets(self, scheduler):
        assert scheduler.filter_by_pet_name(Owner("Empty"), "Rex") == []


# --- Combining filters (the real-world use case) ---------------------------

class TestCombiningFilters:
    def test_rex_incomplete_in_time_order(self, scheduler, owner):
        """Chain: pet's tasks -> only incomplete -> chronological.

        Rex has t1(18:00), t2(09:30), t3(None). None completed, so all three
        survive the completion filter, then sort: t2, t1, t3(None last)."""
        rex_tasks = scheduler.filter_by_pet_name(owner, "Rex")
        incomplete = scheduler.filter_by_completion(rex_tasks, completed=False)
        ordered = scheduler.sort_by_time(incomplete)
        assert [t.id for t in ordered] == ["t2", "t1", "t3"]

    def test_completion_filter_removes_done_task_from_chain(self, scheduler, owner):
        """Complete t2 -> it drops out of the incomplete chain."""
        owner.get_pet("dog1").tasks[1].mark_complete()  # t2 (Morning walk)
        rex_tasks = scheduler.filter_by_pet_name(owner, "Rex")
        incomplete = scheduler.filter_by_completion(rex_tasks, completed=False)
        assert "t2" not in [t.id for t in incomplete]
        assert [t.id for t in scheduler.sort_by_time(incomplete)] == ["t1", "t3"]
