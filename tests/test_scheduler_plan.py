"""Focused test plan for the Scheduler (algorithmic layer of PawPal+).

Covers the three scheduler methods:
  - rank_tasks_by_score(tasks)
  - fit_tasks_in_time(sorted_tasks, minutes)
  - generate_schedule(owner, available_minutes, pet_id)

Tests are grouped and roughly ordered by priority: correctness of the core
algorithm first (ranking + packing), then integration (generate_schedule),
then edge cases and error handling.

Scoring reminder: estimate_score() = priority_weight * duration_minutes,
where low=1, medium=2, high=3.
"""

import pytest

from pawpal_system import Owner, Pet, Task, Schedule, Scheduler


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def make_task(task_id, minutes, priority="medium"):
    """Small factory so test bodies stay about behavior, not construction."""
    return Task(task_id, task_id, minutes, priority=priority)


@pytest.fixture
def scheduler():
    return Scheduler()


@pytest.fixture
def owner_two_pets():
    """Owner 'Priya' with two pets and a spread of priorities/durations.

    Scores:
      Rex   t1 walk   45 high  -> 135
      Rex   t2 train  30 med   ->  60
      Cat   t3 feed   10 high  ->  30
      Cat   t4 laser  20 low   ->  20
    Full-day total = 105 min.
    """
    owner = Owner("Priya")
    rex = Pet("dog1", "Rex", "dog", age=4)
    cat = Pet("cat1", "Whiskers", "cat", age=2)
    owner.add_pet(rex)
    owner.add_pet(cat)
    rex.add_task(make_task("t1", 45, "high"))
    rex.add_task(make_task("t2", 30, "medium"))
    cat.add_task(make_task("t3", 10, "high"))
    cat.add_task(make_task("t4", 20, "low"))
    return owner


# ===========================================================================
# P0 — rank_tasks_by_score: is ranking correct? (highest score first)
# ===========================================================================

class TestRanking:
    def test_orders_highest_score_first(self, scheduler):
        """Setup: three clearly different scores.
        Assert: output ids run high -> low.
        Why: this is the whole point of ranking; everything downstream trusts it."""
        low = make_task("low", 10, "low")     # 10
        mid = make_task("mid", 20, "medium")  # 40
        high = make_task("high", 30, "high")  # 90
        ranked = scheduler.rank_tasks_by_score([low, high, mid])
        assert [t.id for t in ranked] == ["high", "mid", "low"]

    def test_priority_times_duration_not_priority_alone(self, scheduler):
        """Setup: a LOW task long enough to out-score a HIGH short task.
        low 60min = 60 vs high 15min = 45.
        Assert: the long low-priority task ranks first.
        Why: proves the score is priority*duration, not priority tiers."""
        long_low = make_task("long_low", 60, "low")   # 60
        short_high = make_task("short_high", 15, "high")  # 45
        ranked = scheduler.rank_tasks_by_score([short_high, long_low])
        assert [t.id for t in ranked] == ["long_low", "short_high"]

    def test_identical_scores_preserve_input_order(self, scheduler):
        """Setup: three tasks with the SAME score (all 20), given in a known order.
        Assert: order is unchanged (stable sort).
        Why: ties must be deterministic or schedules flicker between runs."""
        a = make_task("a", 20, "medium")  # 40
        b = make_task("b", 20, "medium")  # 40
        c = make_task("c", 20, "medium")  # 40
        ranked = scheduler.rank_tasks_by_score([a, b, c])
        assert [t.id for t in ranked] == ["a", "b", "c"]

    def test_all_same_priority_orders_by_duration(self, scheduler):
        """Setup: all HIGH priority, different durations.
        Assert: longest first (score scales with duration).
        Why: common real case — user marks everything 'high'."""
        ranked = scheduler.rank_tasks_by_score(
            [make_task("s", 10, "high"), make_task("l", 40, "high"), make_task("m", 25, "high")]
        )
        assert [t.id for t in ranked] == ["l", "m", "s"]

    def test_empty_list_returns_empty(self, scheduler):
        """Setup: no tasks.
        Assert: empty list, no crash.
        Why: 0-task days must not raise."""
        assert scheduler.rank_tasks_by_score([]) == []

    def test_single_task(self, scheduler):
        """Setup: one task.
        Assert: list with just that task.
        Why: boundary between empty and many."""
        t = make_task("only", 30, "high")
        assert scheduler.rank_tasks_by_score([t]) == [t]

    def test_does_not_mutate_input(self, scheduler):
        """Setup: an unsorted input list; keep a copy.
        Assert: the original list object is unchanged (sorted returns a new list).
        Why: callers should be able to reuse their list afterwards."""
        original = [make_task("low", 10, "low"), make_task("high", 30, "high")]
        snapshot = list(original)
        scheduler.rank_tasks_by_score(original)
        assert original == snapshot


# ===========================================================================
# P0 — fit_tasks_in_time: is packing correct? (never exceed time; greedy)
# ===========================================================================

class TestPacking:
    def test_takes_all_when_everything_fits(self, scheduler):
        """Setup: total duration < budget.
        Assert: every task kept, in order.
        Why: generous budgets must not drop tasks."""
        tasks = [make_task("a", 10, "high"), make_task("b", 20, "high")]
        fitted = scheduler.fit_tasks_in_time(tasks, minutes=100)
        assert [t.id for t in fitted] == ["a", "b"]

    def test_never_exceeds_budget(self, scheduler):
        """Setup: tasks summing past the budget.
        Assert: total fitted duration <= budget.
        Why: the core invariant — a plan can't overbook the day."""
        tasks = [make_task("a", 45, "high"), make_task("b", 30, "high"), make_task("c", 40, "high")]
        fitted = scheduler.fit_tasks_in_time(tasks, minutes=60)
        assert sum(t.duration_minutes for t in fitted) <= 60

    def test_greedy_continues_past_a_task_that_does_not_fit(self, scheduler):
        """Setup: [45, 30, 10] with 60 min. 45 fits (15 left), 30 can't, 10 fits.
        Assert: result is [a, c] — it did NOT stop at the first miss.
        Why: this 'skip and keep going' behavior is the subtle heart of the packer.
        A stop-at-first-miss bug would return only [a]."""
        tasks = [make_task("a", 45, "high"), make_task("b", 30, "high"), make_task("c", 10, "high")]
        fitted = scheduler.fit_tasks_in_time(tasks, minutes=60)
        assert [t.id for t in fitted] == ["a", "c"]

    def test_task_exactly_equal_to_remaining_fits(self, scheduler):
        """Setup: single 60-min task, 60-min budget.
        Assert: it is included (comparison is <=, not <).
        Why: off-by-one at the boundary is a classic bug."""
        fitted = scheduler.fit_tasks_in_time([make_task("a", 60, "high")], minutes=60)
        assert [t.id for t in fitted] == ["a"]

    def test_task_one_minute_over_is_excluded(self, scheduler):
        """Setup: 61-min task, 60-min budget.
        Assert: excluded.
        Why: the other side of the boundary."""
        fitted = scheduler.fit_tasks_in_time([make_task("a", 61, "high")], minutes=60)
        assert fitted == []

    def test_zero_minutes_fits_nothing(self, scheduler):
        """Setup: real tasks, 0-minute budget.
        Assert: empty result.
        Why: no time -> no plan; must not crash or include a 'free' task."""
        tasks = [make_task("a", 10, "high"), make_task("b", 5, "high")]
        assert scheduler.fit_tasks_in_time(tasks, minutes=0) == []

    def test_empty_task_list_fits_nothing(self, scheduler):
        """Setup: no tasks, plenty of time.
        Assert: empty result.
        Why: 0-task boundary."""
        assert scheduler.fit_tasks_in_time([], minutes=480) == []

    def test_all_tasks_too_big(self, scheduler):
        """Setup: every task longer than the whole budget.
        Assert: nothing fits.
        Why: 'tasks longer than available time' edge case."""
        tasks = [make_task("a", 90, "high"), make_task("b", 120, "high")]
        assert scheduler.fit_tasks_in_time(tasks, minutes=30) == []

    def test_preserves_given_order(self, scheduler):
        """Setup: pass tasks in a deliberate order that all fit.
        Assert: fitted order matches input order.
        Why: fit does NOT re-sort; it trusts the ranked order it's handed."""
        tasks = [make_task("z", 5, "low"), make_task("a", 5, "high")]
        fitted = scheduler.fit_tasks_in_time(tasks, minutes=100)
        assert [t.id for t in fitted] == ["z", "a"]


# ===========================================================================
# P1 — generate_schedule: end-to-end (rank + fit + incomplete + pet filter)
# ===========================================================================

class TestGenerateSchedule:
    def test_returns_schedule_instance(self, scheduler, owner_two_pets):
        """Assert: a Schedule object is returned.
        Why: type contract the Streamlit UI depends on."""
        schedule = scheduler.generate_schedule(owner_two_pets, available_minutes=480)
        assert isinstance(schedule, Schedule)

    def test_full_day_includes_all_tasks(self, scheduler, owner_two_pets):
        """Setup: 480-min budget, 105 min of tasks.
        Assert: all 4 tasks, total 105.
        Why: happy path — everything fits."""
        schedule = scheduler.generate_schedule(owner_two_pets, available_minutes=480)
        assert len(schedule.tasks) == 4
        assert schedule.total_duration() == 105

    def test_output_ordered_high_to_low_score(self, scheduler, owner_two_pets):
        """Assert: scores are non-increasing across the schedule.
        Why: the plan must present most-valuable tasks first."""
        schedule = scheduler.generate_schedule(owner_two_pets, available_minutes=480)
        scores = [t.estimate_score() for t in schedule.tasks]
        assert scores == sorted(scores, reverse=True)

    def test_respects_budget_and_drops_low_priority(self, scheduler, owner_two_pets):
        """Setup: 45-min budget. Ranked: walk45(135), train30(60), feed10(30), laser20(20).
        walk fits (0 left), nothing else fits.
        Assert: only the walk; total <= 45; the low laser is dropped.
        Why: 'does it skip low-priority when out of time?' — yes."""
        schedule = scheduler.generate_schedule(owner_two_pets, available_minutes=45)
        assert [t.id for t in schedule.tasks] == ["t1"]
        assert schedule.total_duration() <= 45

    def test_excludes_completed_tasks(self, scheduler, owner_two_pets):
        """Setup: mark the top task (walk) complete.
        Assert: it never appears in the schedule even with a full day.
        Why: completed work must not be re-planned."""
        owner_two_pets.get_pet("dog1").tasks[0].mark_complete()
        schedule = scheduler.generate_schedule(owner_two_pets, available_minutes=480)
        assert "t1" not in [t.id for t in schedule.tasks]

    def test_all_tasks_completed_gives_empty_schedule(self, scheduler, owner_two_pets):
        """Setup: complete every task.
        Assert: empty schedule (this is the UI's 'nothing to schedule' case).
        Why: must be empty, not an error."""
        for task in owner_two_pets.get_all_tasks():
            task.mark_complete()
        schedule = scheduler.generate_schedule(owner_two_pets, available_minutes=480)
        assert schedule.tasks == []

    def test_single_pet_filter(self, scheduler, owner_two_pets):
        """Setup: pet_id='cat1'.
        Assert: only the cat's tasks appear.
        Why: 'one pet vs all pets' — filtering works."""
        schedule = scheduler.generate_schedule(owner_two_pets, available_minutes=480, pet_id="cat1")
        assert {t.id for t in schedule.tasks} == {"t3", "t4"}

    def test_all_pets_when_no_pet_id(self, scheduler, owner_two_pets):
        """Setup: no pet_id.
        Assert: tasks from BOTH pets appear.
        Why: default should aggregate across pets."""
        schedule = scheduler.generate_schedule(owner_two_pets, available_minutes=480)
        assert {t.id for t in schedule.tasks} == {"t1", "t2", "t3", "t4"}

    def test_single_pet_ignores_other_pets_completed_state(self, scheduler, owner_two_pets):
        """Setup: complete a DOG task, then schedule only the CAT.
        Assert: cat schedule unaffected (2 tasks).
        Why: pet filter must isolate correctly."""
        owner_two_pets.get_pet("dog1").tasks[0].mark_complete()
        schedule = scheduler.generate_schedule(owner_two_pets, available_minutes=480, pet_id="cat1")
        assert len(schedule.tasks) == 2

    def test_pet_with_only_completed_tasks(self, scheduler):
        """Setup: one pet whose sole task is completed.
        Assert: empty schedule for that pet.
        Why: incomplete-filter within a single-pet plan."""
        owner = Owner("Sam")
        pet = Pet("p1", "Rex", "dog", age=2)
        owner.add_pet(pet)
        t = make_task("t1", 30, "high")
        t.mark_complete()
        pet.add_task(t)
        schedule = scheduler.generate_schedule(owner, available_minutes=480, pet_id="p1")
        assert schedule.tasks == []


# ===========================================================================
# P1 — Edge cases: empty owner / no pets / no tasks / zero minutes
# ===========================================================================

class TestEmptyAndZero:
    def test_owner_with_no_pets(self, scheduler):
        """Setup: owner, zero pets.
        Assert: empty schedule, no crash.
        Why: brand-new user with nothing set up."""
        schedule = scheduler.generate_schedule(Owner("New"), available_minutes=480)
        assert schedule.tasks == []

    def test_pet_with_no_tasks(self, scheduler):
        """Setup: a pet but no tasks.
        Assert: empty schedule.
        Why: pet added but no care items yet."""
        owner = Owner("New")
        owner.add_pet(Pet("p1", "Rex", "dog", age=1))
        schedule = scheduler.generate_schedule(owner, available_minutes=480)
        assert schedule.tasks == []

    def test_zero_minutes_schedules_nothing(self, scheduler, owner_two_pets):
        """Setup: real tasks, 0-minute budget (allowed, since >= 0).
        Assert: empty schedule, no error.
        Why: 0 minutes is a valid boundary, distinct from negative."""
        schedule = scheduler.generate_schedule(owner_two_pets, available_minutes=0)
        assert schedule.tasks == []

    def test_zero_minutes_empty_owner(self, scheduler):
        """Setup: no pets AND 0 minutes (double-empty).
        Assert: empty schedule.
        Why: both boundaries at once must still be safe."""
        schedule = scheduler.generate_schedule(Owner("New"), available_minutes=0)
        assert schedule.tasks == []


# ===========================================================================
# P2 — Error handling: invalid arguments must raise
# ===========================================================================

class TestErrors:
    def test_negative_minutes_raises(self, scheduler, owner_two_pets):
        """Setup: available_minutes=-1.
        Assert: ValueError.
        Why: negative time is nonsense and must fail loudly (not silently empty)."""
        with pytest.raises(ValueError):
            scheduler.generate_schedule(owner_two_pets, available_minutes=-1)

    def test_unknown_pet_id_raises(self, scheduler, owner_two_pets):
        """Setup: pet_id that doesn't exist.
        Assert: ValueError.
        Why: a typo'd pet id should surface, not quietly schedule nothing."""
        with pytest.raises(ValueError):
            scheduler.generate_schedule(owner_two_pets, pet_id="ghost")

    def test_unknown_pet_id_raises_even_with_no_pets(self, scheduler):
        """Setup: empty owner + a pet_id.
        Assert: ValueError (missing pet beats 'no tasks').
        Why: filtering to a non-existent pet is still an error."""
        with pytest.raises(ValueError):
            scheduler.generate_schedule(Owner("New"), pet_id="p1")


# ===========================================================================
# P2 — Report: explains chosen and unfitted tasks
# ===========================================================================

class TestReport:
    def test_report_names_owner_and_unfitted(self, scheduler, owner_two_pets):
        """Setup: tight 45-min budget so tasks are left out.
        Assert: report mentions the owner and a 'Did not fit' section.
        Why: the 'why this plan' explanation must list what was dropped."""
        schedule = scheduler.generate_schedule(owner_two_pets, available_minutes=45)
        report = scheduler.get_scheduling_report(owner_two_pets, schedule, minutes=45)
        assert "Priya" in report
        assert "Did not fit" in report

    def test_report_full_day_has_no_unfitted_section(self, scheduler, owner_two_pets):
        """Setup: full day, everything fits.
        Assert: no 'Did not fit' section.
        Why: don't scare the user with an empty leftovers list."""
        schedule = scheduler.generate_schedule(owner_two_pets, available_minutes=480)
        report = scheduler.get_scheduling_report(owner_two_pets, schedule, minutes=480)
        assert "Did not fit" not in report
