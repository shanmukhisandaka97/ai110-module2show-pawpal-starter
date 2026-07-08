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

    # 3. Add tasks with start times. Some deliberately overlap:
    #    - Morning walk 09:00-09:45 overlaps Training 09:30-10:00
    #    - Feed 09:15-09:25 also overlaps the Morning walk
    #    - Laser play 11:00-11:20 has no conflict
    #    - Nap has no start_time (unscheduled) -> never conflicts
    rex.add_task(Task("t1", "Morning walk", 45, priority="high", start_time="09:00"))
    rex.add_task(Task("t2", "Training", 30, priority="medium", start_time="09:30"))
    whiskers.add_task(Task("t3", "Feed", 10, priority="high", start_time="09:15"))
    whiskers.add_task(Task("t4", "Laser play", 20, priority="low", start_time="11:00"))
    whiskers.add_task(Task("t5", "Nap", 60, priority="low"))  # no start_time

    # 4. Build and print today's schedule.
    scheduler = Scheduler()
    schedule = scheduler.generate_schedule(owner, available_minutes=480)

    print("=" * 40)
    print(f"Today's Schedule for {owner.name}")
    print("=" * 40)
    for task in schedule.tasks:
        when = task.start_time if task.start_time else "  --"
        print(f"  {when}  {task.name:<15} {task.duration_minutes:>3} min  ({task.priority})")
    print("-" * 40)
    print(f"  Total: {schedule.total_duration()} min")
    print("=" * 40)

    # 5. Warn about any time conflicts among the scheduled tasks.
    conflicts = scheduler.detect_conflicts(schedule.tasks)
    if conflicts:
        print(f"\n⚠️  {len(conflicts)} time conflict(s) detected:")
        for task_a, task_b in conflicts:
            end_a = scheduler.convert_time_to_minutes(task_a.start_time) + task_a.duration_minutes
            print(
                f"  - '{task_a.name}' ({task_a.start_time}-{end_a // 60:02d}:{end_a % 60:02d}) "
                f"overlaps '{task_b.name}' (starts {task_b.start_time})"
            )
    else:
        print("\n✅ No time conflicts.")


if __name__ == "__main__":
    main()
