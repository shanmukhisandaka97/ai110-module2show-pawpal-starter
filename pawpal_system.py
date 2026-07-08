"""PawPal+ core system.

A small pet-care planning library. It models an :class:`Owner`, their
:class:`Pet` objects, the care :class:`Task` items each pet needs, and a
:class:`Scheduler` that fits the most valuable tasks into a limited daily
time budget, producing a :class:`Schedule` and a human-readable report.

Run this module directly to execute a set of usage examples:

    python pawpal_system.py
"""

from datetime import date, timedelta
from typing import List, Optional, Dict

# Allowed priority values and the score weight each contributes.
VALID_PRIORITIES: Dict[str, int] = {"low": 1, "medium": 2, "high": 3}


def _validate_time(start_time: Optional[str]) -> Optional[str]:
    """Validate an "HH:MM" 24-hour time string.

    Args:
        start_time: A string like ``"09:30"``, or ``None`` for "unscheduled".

    Returns:
        The same string if valid, or ``None`` if ``None`` was passed.

    Raises:
        ValueError: If the string is not a well-formed 24-hour "HH:MM" time.
    """
    if start_time is None:
        return None
    parts = start_time.split(":")
    # Require zero-padded two-digit parts: string sorting in sort_by_time only
    # works chronologically when every time is fixed-width (e.g. "09:30").
    if len(parts) != 2 or not all(len(p) == 2 and p.isdigit() for p in parts):
        raise ValueError(f"start_time must be zero-padded 'HH:MM', got {start_time!r}")
    hours, minutes = int(parts[0]), int(parts[1])
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        raise ValueError(f"start_time out of range (00:00-23:59), got {start_time!r}")
    return start_time


class Owner:
    """A pet owner who owns zero or more pets."""

    def __init__(self, name: str) -> None:
        """Create an owner.

        Args:
            name: The owner's display name.
        """
        self.name: str = name
        self.pets: List["Pet"] = []

    def add_pet(self, pet: "Pet") -> None:
        """Add a pet to this owner.

        Args:
            pet: The :class:`Pet` to add.
        """
        self.pets.append(pet)

    def remove_pet(self, pet_id: str) -> None:
        """Remove a pet by its id.

        Args:
            pet_id: The id of the pet to remove. Unknown ids are ignored.
        """
        self.pets = [pet for pet in self.pets if pet.id != pet_id]

    def get_pet(self, pet_id: str) -> Optional["Pet"]:
        """Return the pet with the given id, or ``None`` if not found.

        Args:
            pet_id: The id of the pet to look up.

        Returns:
            The matching :class:`Pet`, or ``None``.
        """
        for pet in self.pets:
            if pet.id == pet_id:
                return pet
        return None

    def get_all_tasks(self) -> List["Task"]:
        """Return a flat list of every task across all of this owner's pets.

        Returns:
            A single list containing all tasks from all pets, in pet order.
        """
        all_tasks: List["Task"] = []
        for pet in self.pets:
            all_tasks.extend(pet.tasks)
        return all_tasks


class Pet:
    """A pet belonging to an owner, with a list of care tasks."""

    def __init__(self, pet_id: str, name: str, species: str, age: int) -> None:
        """Create a pet.

        Args:
            pet_id: Unique identifier for the pet.
            name: The pet's name.
            species: The pet's species (e.g. ``"dog"``).
            age: The pet's age in years. Must be ``>= 0``.

        Raises:
            ValueError: If ``age`` is negative.
        """
        if age < 0:
            raise ValueError(f"age must be >= 0, got {age}")
        self.id: str = pet_id
        self.name: str = name
        self.species: str = species
        self.age: int = age
        self.tasks: List["Task"] = []

    def add_task(self, task: "Task") -> None:
        """Add a care task to this pet.

        Args:
            task: The :class:`Task` to add.
        """
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove a task by its id.

        Args:
            task_id: The id of the task to remove. Unknown ids are ignored.
        """
        self.tasks = [task for task in self.tasks if task.id != task_id]

    def get_incomplete_tasks(self) -> List["Task"]:
        """Return this pet's tasks that have not yet been completed.

        Returns:
            A list of :class:`Task` objects where ``is_completed`` is ``False``.
        """
        return [task for task in self.tasks if not task.is_completed]


class Task:
    """A single care task for a pet (e.g. a walk, feeding, or grooming)."""

    def __init__(
        self,
        task_id: str,
        name: str,
        duration_minutes: int,
        priority: str = "medium",
        recurring: bool = False,
        start_time: Optional[str] = None,
        due_date: Optional[date] = None,
        interval_days: int = 1,
    ) -> None:
        """Create a task.

        Args:
            task_id: Unique identifier for the task.
            name: Human-readable task name.
            duration_minutes: How long the task takes. Must be ``> 0``.
            priority: One of ``"low"``, ``"medium"``, or ``"high"``.
            recurring: Whether the task repeats regularly.
            start_time: Optional 24-hour "HH:MM" start time (e.g. ``"09:30"``).
                ``None`` means the task has no fixed time yet.
            due_date: Optional calendar date the task is next due.
            interval_days: For recurring tasks, how many days between
                occurrences. Must be ``> 0``. Ignored when ``recurring`` is
                ``False``.

        Raises:
            ValueError: If ``priority`` is invalid, ``duration_minutes`` <= 0,
                ``start_time`` is not a valid "HH:MM" time, or
                ``interval_days`` <= 0.
        """
        if priority not in VALID_PRIORITIES:
            raise ValueError(
                f"priority must be one of {sorted(VALID_PRIORITIES)}, got {priority!r}"
            )
        if duration_minutes <= 0:
            raise ValueError(
                f"duration_minutes must be > 0, got {duration_minutes}"
            )
        if interval_days <= 0:
            raise ValueError(f"interval_days must be > 0, got {interval_days}")
        self.id: str = task_id
        self.name: str = name
        self.duration_minutes: int = duration_minutes
        self.priority: str = priority
        self.recurring: bool = recurring
        self.start_time: Optional[str] = _validate_time(start_time)
        self.due_date: Optional[date] = due_date
        self.interval_days: int = interval_days
        self.is_completed: bool = False

    def estimate_score(self) -> int:
        """Return a value score used to rank this task.

        The score rewards higher priority and longer, more meaningful tasks:
        ``priority_weight * duration_minutes``.

        Returns:
            The task's score as an integer.
        """
        return VALID_PRIORITIES[self.priority] * self.duration_minutes

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.is_completed = True

    def __repr__(self) -> str:
        """Return a concise developer-readable representation of the task."""
        status = "done" if self.is_completed else "todo"
        return (
            f"Task(id={self.id!r}, name={self.name!r}, "
            f"{self.duration_minutes}min, {self.priority}, {status})"
        )


class Schedule:
    """An ordered plan of tasks chosen for a given day."""

    def __init__(self, date: str) -> None:
        """Create an empty schedule.

        Args:
            date: The date this schedule is for (e.g. ``"2026-07-07"``).
        """
        self.date: str = date
        self.tasks: List["Task"] = []

    def add_task(self, task: "Task") -> None:
        """Add a task to the schedule.

        Args:
            task: The :class:`Task` to add.
        """
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove a task by its id.

        Args:
            task_id: The id of the task to remove. Unknown ids are ignored.
        """
        self.tasks = [task for task in self.tasks if task.id != task_id]

    def total_duration(self) -> int:
        """Return the total minutes of all tasks in the schedule.

        Returns:
            Sum of ``duration_minutes`` across scheduled tasks.
        """
        return sum(task.duration_minutes for task in self.tasks)


class Scheduler:
    """Builds a daily :class:`Schedule` from an owner's pending tasks."""

    def rank_tasks_by_score(self, tasks: List["Task"]) -> List["Task"]:
        """Return tasks sorted from most to least valuable.

        Args:
            tasks: The tasks to rank.

        Returns:
            A new list sorted by :meth:`Task.estimate_score` descending.
        """
        return sorted(tasks, key=lambda task: task.estimate_score(), reverse=True)

    def sort_by_time(self, tasks: List["Task"]) -> List["Task"]:
        """Return tasks sorted by start time, earliest first.

        Tasks with no ``start_time`` (``None``) are placed at the end, so a
        chronological view still shows every task. Because "HH:MM" is
        zero-padded and fixed-width, plain string comparison already sorts
        chronologically ("09:30" < "10:00"), so no time parsing is needed.

        Args:
            tasks: The tasks to sort.

        Returns:
            A new list ordered by ``start_time`` ascending, unscheduled last.
        """
        # The key is a tuple: (is_unscheduled, time). ``False`` (0) sorts before
        # ``True`` (1), so scheduled tasks come first; among scheduled tasks the
        # second element orders them by clock time.
        return sorted(
            tasks,
            key=lambda task: (task.start_time is None, task.start_time or ""),
        )

    def filter_by_completion(
        self, tasks: List["Task"], completed: bool
    ) -> List["Task"]:
        """Return only the tasks whose completion state matches ``completed``.

        Args:
            tasks: The tasks to filter.
            completed: ``True`` to keep finished tasks, ``False`` for pending.

        Returns:
            A new list of the matching tasks, original order preserved.
        """
        return [task for task in tasks if task.is_completed == completed]

    def filter_by_pet_name(self, owner: "Owner", pet_name: str) -> List["Task"]:
        """Return every task belonging to pets whose name matches ``pet_name``.

        Matching is case-insensitive. If no pet matches, an empty list is
        returned (rather than raising), so callers can safely chain filters.

        Args:
            owner: The owner whose pets are searched.
            pet_name: The pet name to match (case-insensitive).

        Returns:
            A flat list of that pet's tasks. Returns tasks (not the Pet) so the
            result plugs straight into the other filter/sort methods.
        """
        target = pet_name.lower()
        return [
            task
            for pet in owner.pets
            if pet.name.lower() == target
            for task in pet.tasks
        ]

    def get_pet_schedule(self, owner: "Owner", pet_name: str) -> List["Task"]:
        """Return one pet's incomplete tasks, ordered by start time.

        A convenience that composes the filter/sort primitives: it selects the
        named pet's tasks, drops completed ones, and sorts chronologically
        (unscheduled tasks last).

        Args:
            owner: The owner whose pet is looked up.
            pet_name: The pet name to match (case-insensitive).

        Returns:
            The pet's pending tasks in clock order. Empty if the pet is unknown
            or has no pending tasks.
        """
        pet_tasks = self.filter_by_pet_name(owner, pet_name)
        pending = self.filter_by_completion(pet_tasks, completed=False)
        return self.sort_by_time(pending)

    def convert_time_to_minutes(self, start_time: Optional[str]) -> Optional[int]:
        """Convert an "HH:MM" string to minutes since midnight.

        Args:
            start_time: A zero-padded "HH:MM" time, or ``None``.

        Returns:
            Minutes since 00:00 (e.g. ``"09:30"`` -> ``570``), or ``None`` if
            ``start_time`` is ``None``.
        """
        if start_time is None:
            return None
        hours, minutes = start_time.split(":")
        return int(hours) * 60 + int(minutes)

    def check_time_overlap(self, task_a: "Task", task_b: "Task") -> bool:
        """Return whether two tasks occupy overlapping time spans.

        Each task spans ``[start, start + duration_minutes)``. Tasks that only
        touch at an endpoint (one ends exactly when the other starts) do NOT
        overlap. A task with no ``start_time`` never conflicts (its time is
        unknown), so this returns ``False`` if either task is unscheduled.

        Args:
            task_a: The first task.
            task_b: The second task.

        Returns:
            ``True`` if the two time spans overlap, else ``False``.
        """
        start_a = self.convert_time_to_minutes(task_a.start_time)
        start_b = self.convert_time_to_minutes(task_b.start_time)
        if start_a is None or start_b is None:
            return False
        end_a = start_a + task_a.duration_minutes
        end_b = start_b + task_b.duration_minutes
        # Half-open overlap: strict '<' so adjacent spans (end == start) are fine.
        return start_a < end_b and start_b < end_a

    def detect_conflicts(
        self, tasks: List["Task"]
    ) -> List[tuple]:
        """Find all pairs of tasks whose scheduled times overlap.

        Compares every unique pair once. Tasks without a ``start_time`` are
        ignored (see :meth:`tasks_overlap`).

        Args:
            tasks: The tasks to check for time conflicts.

        Returns:
            A list of ``(task_a, task_b)`` tuples, one per overlapping pair.
            Empty if there are no conflicts.
        """
        conflicts: List[tuple] = []
        for i in range(len(tasks)):
            for j in range(i + 1, len(tasks)):
                if self.check_time_overlap(tasks[i], tasks[j]):
                    conflicts.append((tasks[i], tasks[j]))
        return conflicts

    def get_next_due_date(self, task: "Task") -> Optional[date]:
        """Return the date a recurring task is next due after its current one.

        Uses :class:`datetime.timedelta` to add the task's ``interval_days`` to
        its current ``due_date``. Date arithmetic (leap years, month lengths)
        is handled by the standard library, so we never do it by hand.

        Args:
            task: The task to advance.

        Returns:
            ``due_date + interval_days`` as a :class:`datetime.date`, or
            ``None`` if the task is not recurring or has no ``due_date``.
        """
        if not task.recurring or task.due_date is None:
            return None
        return task.due_date + timedelta(days=task.interval_days)

    def mark_task_complete(self, task: "Task") -> None:
        """Mark a task done, rolling recurring tasks to their next occurrence.

        For a one-off task this just sets ``is_completed``. For a recurring task
        with a ``due_date``, the current occurrence is "finished" by advancing
        ``due_date`` to :meth:`get_next_due_date` and clearing the completed
        flag, so the task reappears on its next scheduled day.

        Args:
            task: The task to complete.
        """
        task.mark_complete()
        if task.recurring and task.due_date is not None:
            task.due_date = self.get_next_due_date(task)
            task.is_completed = False  # reopened for its next occurrence

    def fit_tasks_in_time(
        self, sorted_tasks: List["Task"], minutes: int
    ) -> List["Task"]:
        """Greedily select tasks that fit within a time budget.

        Walks the already-ranked list and takes each task whose duration
        still fits in the remaining minutes.

        Args:
            sorted_tasks: Tasks in priority order (highest value first).
            minutes: Total minutes available.

        Returns:
            The subset of tasks, in order, that fit within ``minutes``.
        """
        fitted: List["Task"] = []
        remaining = minutes
        for task in sorted_tasks:
            if task.duration_minutes <= remaining:
                fitted.append(task)
                remaining -= task.duration_minutes
        return fitted

    def generate_schedule(
        self,
        owner: "Owner",
        available_minutes: int = 480,
        pet_id: Optional[str] = None,
    ) -> "Schedule":
        """Build a schedule of the best-fitting incomplete tasks.

        Considers only incomplete tasks. If ``pet_id`` is given, only that
        pet's tasks are considered; otherwise all pets' tasks are used.

        Args:
            owner: The owner whose tasks are scheduled.
            available_minutes: Time budget for the day (default 480 = 8h).
            pet_id: Optional pet id to restrict scheduling to one pet.

        Returns:
            A :class:`Schedule` populated with the chosen tasks.

        Raises:
            ValueError: If ``available_minutes`` is negative, or ``pet_id``
                is given but no such pet exists.
        """
        if available_minutes < 0:
            raise ValueError(
                f"available_minutes must be >= 0, got {available_minutes}"
            )

        if pet_id is not None:
            pet = owner.get_pet(pet_id)
            if pet is None:
                raise ValueError(f"no pet with id {pet_id!r}")
            candidate_tasks = pet.get_incomplete_tasks()
        else:
            candidate_tasks = [
                task for task in owner.get_all_tasks() if not task.is_completed
            ]

        ranked = self.rank_tasks_by_score(candidate_tasks)
        fitted = self.fit_tasks_in_time(ranked, available_minutes)

        schedule = Schedule(date="today")
        for task in fitted:
            schedule.add_task(task)
        return schedule

    def get_scheduling_report(
        self, owner: "Owner", schedule: "Schedule", minutes: int
    ) -> str:
        """Return a human-readable explanation of a schedule.

        Args:
            owner: The owner the schedule was built for.
            schedule: The schedule to explain.
            minutes: The time budget the schedule was built against.

        Returns:
            A multi-line string summarizing chosen tasks, time used, and
            any incomplete tasks that did not fit.
        """
        scheduled_ids = {task.id for task in schedule.tasks}
        all_incomplete = [
            task for task in owner.get_all_tasks() if not task.is_completed
        ]
        not_fitted = [task for task in all_incomplete if task.id not in scheduled_ids]

        used = schedule.total_duration()
        lines: List[str] = []
        lines.append(f"Scheduling report for {owner.name}")
        lines.append(f"Time budget: {minutes} min | Used: {used} min | Free: {minutes - used} min")
        lines.append("")

        if schedule.tasks:
            lines.append(f"Scheduled {len(schedule.tasks)} task(s), highest value first:")
            for task in schedule.tasks:
                lines.append(
                    f"  - {task.name} ({task.duration_minutes} min, "
                    f"{task.priority} priority, score {task.estimate_score()})"
                )
        else:
            lines.append("No tasks scheduled.")

        if not_fitted:
            lines.append("")
            lines.append("Did not fit in the time budget:")
            for task in not_fitted:
                lines.append(
                    f"  - {task.name} ({task.duration_minutes} min, "
                    f"{task.priority} priority)"
                )

        return "\n".join(lines)


if __name__ == "__main__":
    print("=" * 60)
    print("PawPal+ usage examples")
    print("=" * 60)

    # --- Scenario 1: Build an owner with pets and tasks --------------------
    print("\n[1] Create an owner, pets, and tasks")
    jordan = Owner("Jordan")
    mochi = Pet("p1", "Mochi", "dog", age=3)
    luna = Pet("p2", "Luna", "cat", age=5)
    jordan.add_pet(mochi)
    jordan.add_pet(luna)

    mochi.add_task(Task("t1", "Morning walk", 30, priority="high", recurring=True))
    mochi.add_task(Task("t2", "Vet checkup", 60, priority="high"))
    mochi.add_task(Task("t3", "Brush coat", 15, priority="low"))
    luna.add_task(Task("t4", "Feed", 10, priority="medium", recurring=True))
    luna.add_task(Task("t5", "Play session", 20, priority="medium"))
    print(f"  {jordan.name} has {len(jordan.pets)} pets and "
          f"{len(jordan.get_all_tasks())} total tasks.")

    # --- Scenario 2: Validation catches bad input --------------------------
    print("\n[2] Validation rejects invalid data")
    for label, thunk in [
        ("bad priority", lambda: Task("x", "Bad", 10, priority="urgent")),
        ("zero duration", lambda: Task("x", "Bad", 0)),
        ("negative age", lambda: Pet("x", "Bad", "dog", age=-1)),
    ]:
        try:
            thunk()
        except ValueError as err:
            print(f"  {label}: rejected -> {err}")

    # --- Scenario 3: Owner.get_all_tasks() ---------------------------------
    print("\n[3] Owner.get_all_tasks() flattens across pets")
    for task in jordan.get_all_tasks():
        print(f"  {task.name}")

    # --- Scenario 4: Completion tracking + get_incomplete_tasks() ----------
    print("\n[4] Mark a task complete and list incomplete ones")
    mochi.tasks[2].mark_complete()  # Brush coat done
    print(f"  Mochi incomplete tasks: "
          f"{[t.name for t in mochi.get_incomplete_tasks()]}")

    # --- Scenario 5: Generate a schedule for all pets ----------------------
    print("\n[5] Generate a full-day schedule (480 min)")
    scheduler = Scheduler()
    schedule = scheduler.generate_schedule(jordan, available_minutes=480)
    print(f"  Scheduled: {[t.name for t in schedule.tasks]}")
    print(f"  Total: {schedule.total_duration()} min")

    # --- Scenario 6: Tight time budget forces trade-offs -------------------
    print("\n[6] Tight budget (45 min) picks highest-value tasks")
    tight = scheduler.generate_schedule(jordan, available_minutes=45)
    print(f"  Scheduled: {[t.name for t in tight.tasks]}")
    print(scheduler.get_scheduling_report(jordan, tight, minutes=45))

    # --- Scenario 7: Schedule for a single pet -----------------------------
    print("\n[7] Schedule for one pet only (Luna)")
    luna_schedule = scheduler.generate_schedule(
        jordan, available_minutes=480, pet_id="p2"
    )
    print(f"  Scheduled: {[t.name for t in luna_schedule.tasks]}")

    print("\n" + "=" * 60)
    print("All scenarios ran successfully.")
    print("=" * 60)
