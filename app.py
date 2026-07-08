import streamlit as st

from pawpal_system import Owner, Pet, Task, Schedule, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

# ---------------------------------------------------------------------------
# Persist the Owner across reruns. Created ONCE; every later rerun reuses it.
# ---------------------------------------------------------------------------
owner_name = st.text_input("Owner name", value="Jordan")

if "owner" not in st.session_state:
    st.session_state.owner = Owner(owner_name)

owner = st.session_state.owner
# Keep the owner's name in sync with the text box.
owner.name = owner_name

# One Scheduler drives all sorting, filtering, and conflict checks below.
scheduler = Scheduler()


def _pet_of(task):
    """Return the name of the pet that owns ``task``, or None."""
    for pet in owner.pets:
        if any(t is task for t in pet.tasks):
            return pet.name
    return None


def _end_time(task):
    """Return the "HH:MM" end time of a scheduled task."""
    total = scheduler.convert_time_to_minutes(task.start_time) + task.duration_minutes
    return f"{total // 60:02d}:{total % 60:02d}"


def show_conflict(task_a, task_b):
    """Render one conflict as a pet-owner-friendly, actionable warning.

    Instead of a bare "these overlap", it names the pets, shows the exact
    clock window each task occupies and the overlapping minutes, and suggests
    a concrete fix — so the owner knows *what* clashes and *how* to resolve it.
    """
    start_a = scheduler.convert_time_to_minutes(task_a.start_time)
    start_b = scheduler.convert_time_to_minutes(task_b.start_time)
    end_a = start_a + task_a.duration_minutes
    end_b = start_b + task_b.duration_minutes
    overlap = min(end_a, end_b) - max(start_a, start_b)

    def label(task):
        pet = _pet_of(task)
        who = f" for {pet}" if pet else ""
        return f"**{task.name}**{who} ({task.start_time}–{_end_time(task)})"

    # Move the shorter task so the fix is the least disruptive.
    to_move = task_a if task_a.duration_minutes <= task_b.duration_minutes else task_b
    st.warning(
        f"⏰ Schedule clash — {label(task_a)} and {label(task_b)} "
        f"overlap by **{overlap} min**. "
        f"Try moving **{to_move.name}** to a free slot, or shorten one of them."
    )

# ---------------------------------------------------------------------------
# Add a Pet -> handled by Owner.add_pet(Pet(...))
# ---------------------------------------------------------------------------
st.subheader("Add a Pet")
with st.form("add_pet_form"):
    col1, col2 = st.columns(2)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
        species = st.selectbox("Species", ["dog", "cat", "other"])
    with col2:
        age = st.number_input("Age (years)", min_value=0, max_value=40, value=3)
    submitted_pet = st.form_submit_button("Add pet")

if submitted_pet:
    try:
        new_id = f"p{len(owner.pets) + 1}"
        # Owner.add_pet is the method that handles the submitted data.
        owner.add_pet(Pet(new_id, pet_name, species, age=int(age)))
        st.success(f"Added {pet_name} the {species}.")
    except ValueError as err:
        st.error(f"Could not add pet: {err}")

# Display current pets (re-read from the persisted owner on every rerun).
if owner.pets:
    st.write("**Your pets:**")
    for pet in owner.pets:
        st.write(
            f"- {pet.name} ({pet.species}, age {pet.age}) — "
            f"{len(pet.tasks)} task(s)"
        )
else:
    st.info("No pets yet. Add one above.")

st.divider()

# ---------------------------------------------------------------------------
# Add a Task -> handled by Pet.add_task(Task(...))
# ---------------------------------------------------------------------------
st.subheader("Add a Task")
if not owner.pets:
    st.info("Add a pet first before scheduling tasks.")
else:
    with st.form("add_task_form"):
        # Pick which pet the task belongs to.
        pet_labels = {pet.name: pet for pet in owner.pets}
        chosen_pet_name = st.selectbox("For pet", list(pet_labels.keys()))
        col1, col2, col3 = st.columns(3)
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
        with col2:
            duration = st.number_input(
                "Duration (minutes)", min_value=1, max_value=240, value=20
            )
        with col3:
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        # Optional start time; leave blank for an unscheduled task.
        start_time_str = st.text_input("Start time (HH:MM, optional)", value="")
        submitted_task = st.form_submit_button("Add task")

    if submitted_task:
        try:
            pet = pet_labels[chosen_pet_name]
            task_id = f"t{len(owner.get_all_tasks()) + 1}"
            # Blank start time -> None (unscheduled); Task validates the format.
            start_time = start_time_str.strip() or None
            # Pet.add_task is the method that handles the submitted data.
            pet.add_task(
                Task(
                    task_id, task_title, int(duration),
                    priority=priority, start_time=start_time,
                )
            )
            st.success(f"Added '{task_title}' to {pet.name}.")
        except ValueError as err:
            st.error(f"Could not add task: {err}")

    # Show tasks across pets, sorted and filtered via the Scheduler methods.
    all_tasks = owner.get_all_tasks()
    if all_tasks:
        st.write("**Current tasks:**")

        # Filter controls -> Scheduler.filter_by_pet_name / filter_by_completion
        fcol1, fcol2 = st.columns(2)
        with fcol1:
            pet_filter = st.selectbox(
                "Filter by pet", ["All pets"] + [p.name for p in owner.pets]
            )
        with fcol2:
            status_filter = st.radio(
                "Status", ["All", "Pending", "Done"], horizontal=True
            )

        # Start from the selected pet's tasks (or everything).
        if pet_filter == "All pets":
            tasks = all_tasks
        else:
            tasks = scheduler.filter_by_pet_name(owner, pet_filter)

        # Apply the completion filter.
        if status_filter == "Pending":
            tasks = scheduler.filter_by_completion(tasks, completed=False)
        elif status_filter == "Done":
            tasks = scheduler.filter_by_completion(tasks, completed=True)

        # Present them in chronological order (unscheduled tasks trail last).
        tasks = scheduler.sort_by_time(tasks)

        if tasks:
            st.table(
                [
                    {
                        "task": t.name,
                        "start": t.start_time or "—",
                        "minutes": t.duration_minutes,
                        "priority": t.priority,
                        "done": "✅" if t.is_completed else "",
                    }
                    for t in tasks
                ]
            )

            # Flag overlapping start times right here on the task list.
            conflicts = scheduler.detect_conflicts(tasks)
            if conflicts:
                st.write(f"**{len(conflicts)} time conflict(s) found:**")
                for task_a, task_b in conflicts:
                    show_conflict(task_a, task_b)
            else:
                st.success("✅ No time conflicts among these tasks.")
        else:
            st.info("No tasks match the current filters.")

st.divider()

# ---------------------------------------------------------------------------
# Build Schedule -> handled by Scheduler.generate_schedule(owner, ...)
# ---------------------------------------------------------------------------
st.subheader("Build Schedule")
available_minutes = st.slider("Available minutes today", 30, 480, 480, step=15)

if st.button("Generate schedule"):
    schedule = scheduler.generate_schedule(owner, available_minutes=available_minutes)
    if schedule.tasks:
        used = schedule.total_duration()
        st.success(
            f"✅ Planned {len(schedule.tasks)} task(s) — "
            f"{used} of {available_minutes} min used, {available_minutes - used} min free."
        )

        # Show the plan chronologically so it reads like a real day.
        st.table(
            [
                {
                    "start": t.start_time or "—",
                    "task": t.name,
                    "pet": _pet_of(t) or "—",
                    "minutes": t.duration_minutes,
                    "priority": t.priority,
                }
                for t in scheduler.sort_by_time(schedule.tasks)
            ]
        )

        # Warn about any tasks whose start times overlap, with a helpful fix.
        conflicts = scheduler.detect_conflicts(schedule.tasks)
        if conflicts:
            for task_a, task_b in conflicts:
                show_conflict(task_a, task_b)
        else:
            st.success("✅ No time conflicts in this plan.")

        # Plain-language explanation of what was chosen and what didn't fit.
        report = scheduler.get_scheduling_report(owner, schedule, available_minutes)
        with st.expander("Why this plan?"):
            st.text(report)
    else:
        st.warning("No incomplete tasks to schedule. Add some tasks above.")

# ---------------------------------------------------------------------------
# Debug: inspect what's actually stored in the session.
# ---------------------------------------------------------------------------
with st.expander("🐛 Debug: session_state"):
    st.write(st.session_state)
