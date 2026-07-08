"""PawPal+ demo script.

Creates an owner with pets and tasks, then prints today's schedule.

Run in the terminal:

    python main.py
"""

from pawpal_system import Owner, Pet, Task, Scheduler


def main() -> None:
    # 1. Create an owner.
    owner = Owner("Priya")

    # 2. Create at least two pets and add them to the owner.
    rex = Pet("dog1", "Rex", "dog", age=4)
    whiskers = Pet("cat1", "Whiskers", "cat", age=2)
    owner.add_pet(rex)
    owner.add_pet(whiskers)

    # 3. Add at least three tasks with different durations.
    rex.add_task(Task("t1", "Morning walk", 45, priority="high"))
    rex.add_task(Task("t2", "Training", 30, priority="medium"))
    whiskers.add_task(Task("t3", "Feed", 10, priority="high"))
    whiskers.add_task(Task("t4", "Laser play", 20, priority="low"))

    # 4. Build and print today's schedule.
    scheduler = Scheduler()
    schedule = scheduler.generate_schedule(owner, available_minutes=480)

    print("=" * 40)
    print(f"Today's Schedule for {owner.name}")
    print("=" * 40)
    for task in schedule.tasks:
        print(f"  {task.name:<15} {task.duration_minutes:>3} min  ({task.priority})")
    print("-" * 40)
    print(f"  Total: {schedule.total_duration()} min")
    print("=" * 40)


if __name__ == "__main__":
    main()
