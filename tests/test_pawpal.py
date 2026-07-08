"""Tests for the PawPal+ system."""

import pytest

from pawpal_system import Owner, Pet, Task, Schedule, Scheduler


# --- Simple starter tests --------------------------------------------------

def test_task_completion():
    """Calling mark_complete() changes the task's status to completed."""
    task = Task("t1", "Morning walk", 30, priority="high")
    assert task.is_completed is False   # starts incomplete
    task.mark_complete()
    assert task.is_completed is True    # now complete


def test_task_addition():
    """Adding a task to a Pet increases that pet's task count."""
    pet = Pet("dog1", "Rex", "dog", age=4)
    assert len(pet.tasks) == 0
    pet.add_task(Task("t1", "Feed", 10, priority="medium"))
    assert len(pet.tasks) == 1


# --- Fixtures --------------------------------------------------------------

@pytest.fixture
def owner_with_pets():
    """An owner with two pets and a spread of tasks."""
    owner = Owner("Priya")
    rex = Pet("dog1", "Rex", "dog", age=4)
    whiskers = Pet("cat1", "Whiskers", "cat", age=2)
    owner.add_pet(rex)
    owner.add_pet(whiskers)

    rex.add_task(Task("t1", "Morning walk", 45, priority="high"))
    rex.add_task(Task("t2", "Training", 30, priority="medium"))
    whiskers.add_task(Task("t3", "Feed", 10, priority="high"))
    whiskers.add_task(Task("t4", "Laser play", 20, priority="low"))
    return owner


# --- Validation ------------------------------------------------------------

class TestValidation:
    def test_invalid_priority_raises(self):
        with pytest.raises(ValueError):
            Task("x", "Bad", 10, priority="urgent")

    def test_valid_priorities_accepted(self):
        for priority in ("low", "medium", "high"):
            task = Task("x", "OK", 10, priority=priority)
            assert task.priority == priority

    def test_zero_duration_raises(self):
        with pytest.raises(ValueError):
            Task("x", "Bad", 0)

    def test_negative_duration_raises(self):
        with pytest.raises(ValueError):
            Task("x", "Bad", -5)

    def test_negative_age_raises(self):
        with pytest.raises(ValueError):
            Pet("x", "Bad", "dog", age=-1)

    def test_zero_age_allowed(self):
        pet = Pet("x", "Newborn", "cat", age=0)
        assert pet.age == 0


# --- Task behavior ---------------------------------------------------------

class TestTask:
    def test_estimate_score(self):
        # priority weight (high=3) * duration
        assert Task("x", "Walk", 30, priority="high").estimate_score() == 90
        assert Task("x", "Feed", 10, priority="medium").estimate_score() == 20
        assert Task("x", "Brush", 15, priority="low").estimate_score() == 15

    def test_tasks_start_incomplete(self):
        assert Task("x", "Walk", 30).is_completed is False

    def test_mark_complete(self):
        task = Task("x", "Walk", 30)
        task.mark_complete()
        assert task.is_completed is True


# --- Owner / Pet -----------------------------------------------------------

class TestOwnerPet:
    def test_add_and_remove_pet(self, owner_with_pets):
        assert len(owner_with_pets.pets) == 2
        owner_with_pets.remove_pet("dog1")
        assert len(owner_with_pets.pets) == 1
        assert owner_with_pets.get_pet("dog1") is None

    def test_get_pet(self, owner_with_pets):
        assert owner_with_pets.get_pet("cat1").name == "Whiskers"
        assert owner_with_pets.get_pet("nope") is None

    def test_get_all_tasks_flattens(self, owner_with_pets):
        names = {t.name for t in owner_with_pets.get_all_tasks()}
        assert names == {"Morning walk", "Training", "Feed", "Laser play"}
        assert len(owner_with_pets.get_all_tasks()) == 4

    def test_remove_task(self, owner_with_pets):
        rex = owner_with_pets.get_pet("dog1")
        rex.remove_task("t1")
        assert "t1" not in [t.id for t in rex.tasks]

    def test_get_incomplete_tasks(self, owner_with_pets):
        rex = owner_with_pets.get_pet("dog1")
        rex.tasks[0].mark_complete()
        incomplete = rex.get_incomplete_tasks()
        assert len(incomplete) == 1
        assert incomplete[0].name == "Training"


# --- Scheduler -------------------------------------------------------------

class TestScheduler:
    def test_rank_tasks_by_score(self):
        scheduler = Scheduler()
        low = Task("a", "Low", 10, priority="low")      # score 10
        high = Task("b", "High", 30, priority="high")   # score 90
        mid = Task("c", "Mid", 20, priority="medium")   # score 40
        ranked = scheduler.rank_tasks_by_score([low, high, mid])
        assert [t.id for t in ranked] == ["b", "c", "a"]

    def test_fit_tasks_in_time(self):
        scheduler = Scheduler()
        tasks = [
            Task("a", "A", 45, priority="high"),
            Task("b", "B", 30, priority="high"),
            Task("c", "C", 10, priority="high"),
        ]
        fitted = scheduler.fit_tasks_in_time(tasks, minutes=60)
        # 45 fits (15 left), 30 doesn't, 10 fits (5 left)
        assert [t.id for t in fitted] == ["a", "c"]

    def test_generate_schedule_full_day(self, owner_with_pets):
        scheduler = Scheduler()
        schedule = scheduler.generate_schedule(owner_with_pets, available_minutes=480)
        assert isinstance(schedule, Schedule)
        assert len(schedule.tasks) == 4
        assert schedule.total_duration() == 105

    def test_generate_schedule_respects_budget(self, owner_with_pets):
        scheduler = Scheduler()
        schedule = scheduler.generate_schedule(owner_with_pets, available_minutes=60)
        assert schedule.total_duration() <= 60

    def test_generate_schedule_orders_by_score(self, owner_with_pets):
        scheduler = Scheduler()
        schedule = scheduler.generate_schedule(owner_with_pets, available_minutes=480)
        scores = [t.estimate_score() for t in schedule.tasks]
        assert scores == sorted(scores, reverse=True)

    def test_generate_schedule_skips_completed(self, owner_with_pets):
        scheduler = Scheduler()
        # Complete the highest-value task; it should not be scheduled.
        owner_with_pets.get_pet("dog1").tasks[0].mark_complete()
        schedule = scheduler.generate_schedule(owner_with_pets, available_minutes=480)
        assert "Morning walk" not in [t.name for t in schedule.tasks]

    def test_generate_schedule_for_single_pet(self, owner_with_pets):
        scheduler = Scheduler()
        schedule = scheduler.generate_schedule(
            owner_with_pets, available_minutes=480, pet_id="cat1"
        )
        assert {t.name for t in schedule.tasks} == {"Feed", "Laser play"}

    def test_generate_schedule_unknown_pet_raises(self, owner_with_pets):
        scheduler = Scheduler()
        with pytest.raises(ValueError):
            scheduler.generate_schedule(owner_with_pets, pet_id="ghost")

    def test_generate_schedule_negative_minutes_raises(self, owner_with_pets):
        scheduler = Scheduler()
        with pytest.raises(ValueError):
            scheduler.generate_schedule(owner_with_pets, available_minutes=-1)

    def test_scheduling_report_mentions_unfitted(self, owner_with_pets):
        scheduler = Scheduler()
        schedule = scheduler.generate_schedule(owner_with_pets, available_minutes=45)
        report = scheduler.get_scheduling_report(owner_with_pets, schedule, minutes=45)
        assert "Priya" in report
        assert "Did not fit" in report


# --- Schedule --------------------------------------------------------------

class TestSchedule:
    def test_add_and_total_duration(self):
        schedule = Schedule("today")
        schedule.add_task(Task("a", "A", 30))
        schedule.add_task(Task("b", "B", 15))
        assert schedule.total_duration() == 45

    def test_remove_task(self):
        schedule = Schedule("today")
        schedule.add_task(Task("a", "A", 30))
        schedule.remove_task("a")
        assert schedule.total_duration() == 0
