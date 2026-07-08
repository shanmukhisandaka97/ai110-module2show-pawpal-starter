"""PawPal+ core system.

A small pet-care planning library. It models an :class:`Owner`, their
:class:`Pet` objects, the care :class:`Task` items each pet needs, and a
:class:`Scheduler` that fits the most valuable tasks into a limited daily
time budget, producing a :class:`Schedule` and a human-readable report.

Run this module directly to execute a set of usage examples:

    python pawpal_system.py
"""

from typing import List, Optional, Dict

# Allowed priority values and the score weight each contributes.
VALID_PRIORITIES: Dict[str, int] = {"low": 1, "medium": 2, "high": 3}


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
    ) -> None:
        """Create a task.

        Args:
            task_id: Unique identifier for the task.
            name: Human-readable task name.
            duration_minutes: How long the task takes. Must be ``> 0``.
            priority: One of ``"low"``, ``"medium"``, or ``"high"``.
            recurring: Whether the task repeats regularly.

        Raises:
            ValueError: If ``priority`` is invalid or ``duration_minutes`` <= 0.
        """
        if priority not in VALID_PRIORITIES:
            raise ValueError(
                f"priority must be one of {sorted(VALID_PRIORITIES)}, got {priority!r}"
            )
        if duration_minutes <= 0:
            raise ValueError(
                f"duration_minutes must be > 0, got {duration_minutes}"
            )
        self.id: str = task_id
        self.name: str = name
        self.duration_minutes: int = duration_minutes
        self.priority: str = priority
        self.recurring: bool = recurring
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
