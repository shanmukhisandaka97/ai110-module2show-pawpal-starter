"""Tests for conflict detection, get_pet_schedule, and recurring tasks.

Run from repo root:  python -m pytest tests/test_conflicts_recurring.py -q
"""

from datetime import date

import pytest

from pawpal_system import Owner, Pet, Task, Scheduler


@pytest.fixture
def scheduler():
    return Scheduler()


# --- convert_time_to_minutes -----------------------------------------------

class TestConvertTime:
    def test_basic(self, scheduler):
        assert scheduler.convert_time_to_minutes("00:00") == 0
        assert scheduler.convert_time_to_minutes("09:30") == 570
        assert scheduler.convert_time_to_minutes("23:59") == 1439

    def test_none_returns_none(self, scheduler):
        assert scheduler.convert_time_to_minutes(None) is None


# --- check_time_overlap ----------------------------------------------------

class TestOverlap:
    def test_clear_overlap(self, scheduler):
        a = Task("a", "A", 45, start_time="09:00")  # 09:00-09:45
        b = Task("b", "B", 30, start_time="09:30")  # 09:30-10:00
        assert scheduler.check_time_overlap(a, b) is True

    def test_adjacent_is_not_overlap(self, scheduler):
        """One ends exactly when the next starts -> NOT a conflict."""
        a = Task("a", "A", 30, start_time="09:00")  # ends 09:30
        b = Task("b", "B", 30, start_time="09:30")  # starts 09:30
        assert scheduler.check_time_overlap(a, b) is False

    def test_disjoint(self, scheduler):
        a = Task("a", "A", 10, start_time="08:00")
        b = Task("b", "B", 10, start_time="12:00")
        assert scheduler.check_time_overlap(a, b) is False

    def test_contained(self, scheduler):
        """A short task fully inside a long one still conflicts."""
        big = Task("big", "Big", 120, start_time="09:00")   # 09:00-11:00
        small = Task("small", "Small", 10, start_time="10:00")
        assert scheduler.check_time_overlap(big, small) is True

    def test_none_start_time_never_conflicts(self, scheduler):
        scheduled = Task("s", "S", 60, start_time="09:00")
        unscheduled = Task("u", "U", 60)  # no start_time
        assert scheduler.check_time_overlap(scheduled, unscheduled) is False
        assert scheduler.check_time_overlap(unscheduled, unscheduled) is False


# --- detect_conflicts ------------------------------------------------------

class TestDetectConflicts:
    def test_finds_overlapping_pair(self, scheduler):
        tasks = [
            Task("a", "A", 45, start_time="09:00"),
            Task("b", "B", 30, start_time="09:30"),
            Task("c", "C", 20, start_time="11:00"),
        ]
        conflicts = scheduler.detect_conflicts(tasks)
        assert len(conflicts) == 1
        assert {conflicts[0][0].id, conflicts[0][1].id} == {"a", "b"}

    def test_multiple_conflicts(self, scheduler):
        """One task overlapping two others yields two pairs."""
        tasks = [
            Task("a", "A", 60, start_time="09:00"),  # 09:00-10:00
            Task("b", "B", 10, start_time="09:15"),
            Task("c", "C", 10, start_time="09:45"),
        ]
        conflicts = scheduler.detect_conflicts(tasks)
        assert len(conflicts) == 2

    def test_each_pair_once(self, scheduler):
        """3 mutually overlapping tasks -> exactly 3 pairs, no duplicates."""
        tasks = [Task(x, x, 60, start_time="09:00") for x in ("a", "b", "c")]
        assert len(scheduler.detect_conflicts(tasks)) == 3

    def test_no_conflicts(self, scheduler):
        tasks = [
            Task("a", "A", 30, start_time="08:00"),
            Task("b", "B", 30, start_time="09:00"),
        ]
        assert scheduler.detect_conflicts(tasks) == []

    def test_empty_and_single(self, scheduler):
        assert scheduler.detect_conflicts([]) == []
        assert scheduler.detect_conflicts([Task("a", "A", 30, start_time="09:00")]) == []

    def test_ignores_unscheduled(self, scheduler):
        tasks = [Task("a", "A", 60), Task("b", "B", 60)]  # both None
        assert scheduler.detect_conflicts(tasks) == []


# --- get_pet_schedule ------------------------------------------------------

class TestGetPetSchedule:
    @pytest.fixture
    def owner(self):
        o = Owner("Priya")
        rex = Pet("dog1", "Rex", "dog", age=4)
        o.add_pet(rex)
        rex.add_task(Task("t1", "Evening", 30, start_time="18:00"))
        rex.add_task(Task("t2", "Morning", 30, start_time="07:00"))
        done = Task("t3", "Done", 30, start_time="12:00")
        done.mark_complete()
        rex.add_task(done)
        rex.add_task(Task("t4", "Someday", 30))  # no start_time
        return o

    def test_pending_in_time_order_unscheduled_last(self, scheduler, owner):
        result = scheduler.get_pet_schedule(owner, "Rex")
        assert [t.id for t in result] == ["t2", "t1", "t4"]  # t3 done -> excluded

    def test_case_insensitive(self, scheduler, owner):
        assert len(scheduler.get_pet_schedule(owner, "rex")) == 3

    def test_unknown_pet_empty(self, scheduler, owner):
        assert scheduler.get_pet_schedule(owner, "Ghost") == []


# --- Recurring tasks -------------------------------------------------------

class TestRecurring:
    def test_interval_days_validation(self):
        with pytest.raises(ValueError):
            Task("x", "Bad", 10, recurring=True, interval_days=0)

    def test_get_next_due_date_daily(self, scheduler):
        task = Task("t", "Feed", 10, recurring=True,
                    due_date=date(2026, 7, 7), interval_days=1)
        assert scheduler.get_next_due_date(task) == date(2026, 7, 8)

    def test_get_next_due_date_weekly_crosses_month(self, scheduler):
        """timedelta handles month rollover for us."""
        task = Task("t", "Groom", 30, recurring=True,
                    due_date=date(2026, 7, 30), interval_days=7)
        assert scheduler.get_next_due_date(task) == date(2026, 8, 6)

    def test_non_recurring_has_no_next_due(self, scheduler):
        task = Task("t", "Vet", 60, due_date=date(2026, 7, 7))  # recurring=False
        assert scheduler.get_next_due_date(task) is None

    def test_recurring_without_due_date(self, scheduler):
        task = Task("t", "Feed", 10, recurring=True)  # no due_date
        assert scheduler.get_next_due_date(task) is None

    def test_mark_complete_rolls_recurring_forward(self, scheduler):
        """Completing a recurring task advances its due date and reopens it."""
        task = Task("t", "Feed", 10, recurring=True,
                    due_date=date(2026, 7, 7), interval_days=1)
        scheduler.mark_task_complete(task)
        assert task.due_date == date(2026, 7, 8)
        assert task.is_completed is False  # reopened for next occurrence

    def test_mark_complete_one_off_stays_complete(self, scheduler):
        task = Task("t", "Vet", 60)  # not recurring
        scheduler.mark_task_complete(task)
        assert task.is_completed is True
