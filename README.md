# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Terminal output from running `python main.py`:

```
========================================
Today's Schedule for Priya
========================================
  09:00  Morning walk     45 min  (high)
  09:30  Training         30 min  (medium)
    --  Nap              60 min  (low)
  09:15  Feed             10 min  (high)
  11:00  Laser play       20 min  (low)
----------------------------------------
  Total: 165 min
========================================

⚠️  2 time conflict(s) detected:
  - 'Morning walk' (09:00-09:45) overlaps 'Training' (starts 09:30)
  - 'Morning walk' (09:00-09:45) overlaps 'Feed' (starts 09:15)
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run a single test file:
pytest tests/test_pawpal.py -q

# Run with coverage:
pytest --cov
```

The suite lives in `tests/` and covers the core scheduling behaviors:

| File | What it covers |
|------|----------------|
| `test_pawpal.py` | Validation, Owner/Pet/Task behavior, scheduling, and the key rubric behaviors: chronological sorting, recurrence roll-forward, and conflict detection |
| `test_sort_filter.py` | `sort_by_time`, `filter_by_completion`, `filter_by_pet_name`, and `start_time` validation |
| `test_conflicts_recurring.py` | Time-overlap and conflict detection, `get_pet_schedule`, and recurring-task due-date logic |
| `test_scheduler_plan.py` | Schedule generation and time-budget planning |

Three behaviors are exercised end to end:

- **Sorting correctness** — tasks are returned in chronological order, with unscheduled (no `start_time`) tasks trailing last.
- **Recurrence logic** — completing a daily task advances its `due_date` by `interval_days` and reopens it for the next day.
- **Conflict detection** — the scheduler flags tasks whose time spans overlap (including duplicate start times).

Sample test output:

```
$ pytest -q
........................................................................ [ 61%]
.............................................                            [100%]
117 passed in 0.05s
```

## ✨ Features

PawPal+ implements the following scheduling algorithms, all driven by the
stateless `Scheduler` class in `pawpal_system.py`:

| Feature | Method(s) | What it does |
|---------|-----------|--------------|
| **Value-based ranking** | `rank_tasks_by_score`, `Task.estimate_score` | Scores each task as `priority_weight × duration_minutes` (low=1, medium=2, high=3) and ranks highest-value first. |
| **Time-budget planning** | `generate_schedule`, `fit_tasks_in_time` | Greedily fits the highest-value tasks into a fixed daily minute budget (default 480 = 8h), skipping any that no longer fit. |
| **Sorting by time** | `sort_by_time` | Orders tasks chronologically by `start_time`; unscheduled tasks (no start time) trail at the end. |
| **Filtering** | `filter_by_completion`, `filter_by_pet_name`, `get_pet_schedule` | Narrows tasks by completion status or by pet (case-insensitive), and composes both into a single pet's pending, time-sorted plan. |
| **Conflict warnings** | `detect_conflicts`, `check_time_overlap`, `convert_time_to_minutes` | Flags every pair of tasks whose `[start, start+duration)` windows overlap. Adjacent tasks (one ends exactly as the next starts) and unscheduled tasks never conflict. |
| **Daily / recurring tasks** | `mark_task_complete`, `get_next_due_date` | Completing a recurring task rolls its `due_date` forward by `interval_days` and reopens it for its next occurrence; one-off tasks simply close. |
| **Plain-language reporting** | `get_scheduling_report` | Explains the plan: tasks chosen (highest value first), minutes used vs. free, and which incomplete tasks did not fit. |
| **Input validation** | `Task.__init__`, `Pet.__init__`, `_validate_time` | Rejects invalid priorities, non-positive durations, negative ages, bad `interval_days`, and malformed `HH:MM` start times. |

## 🎬 Demo Walkthrough

PawPal+ runs two ways: an interactive Streamlit app (`app.py`) and a scripted
terminal demo (`main.py`). This section walks through both in plain text.

### Launch the app

```bash
streamlit run app.py
```

### Main UI features & available actions

The Streamlit page is a single scrolling form. From top to bottom a user can:

- **Set the owner** — type an owner name; it persists across reruns via
  `st.session_state`.
- **Add a pet** — enter a name, species (dog / cat / other), and age. Added
  pets are listed with their task counts. Invalid input (e.g. negative age) is
  rejected with an inline error.
- **Add a task** — pick which pet it belongs to, then set a title, duration,
  priority (low / medium / high), and an optional `HH:MM` start time (leave
  blank for an unscheduled task).
- **Browse tasks** — the current task list can be **filtered** by pet and by
  status (All / Pending / Done), and is always shown in **chronological order**.
  Overlapping tasks trigger inline **conflict warnings**.
- **Build a schedule** — choose the available minutes for the day with a slider
  (30–480) and click **Generate schedule**. The plan is shown chronologically
  with per-task pet, duration, and priority, plus conflict warnings and a
  **"Why this plan?"** explanation of what was chosen and what didn't fit.

### Example workflow

1. Set the owner name to **Jordan**.
2. **Add a pet:** `Mochi`, a dog, age 3.
3. **Add tasks** for Mochi: `Morning walk` (45 min, high, `09:00`) and
   `Training` (30 min, medium, `09:30`).
4. The task list shows both tasks in time order and warns that they **overlap
   by 15 minutes**, suggesting you move the shorter task.
5. Set the daily budget to **480 minutes** and click **Generate schedule**.
6. View **today's schedule** — the highest-value tasks are planned first, the
   overlap warning repeats on the plan, and **"Why this plan?"** reports the
   minutes used vs. free.

### Key Scheduler behaviors on display

- **Value-based selection** — `generate_schedule` picks tasks by score
  (`priority × duration`), so higher-priority, longer tasks are chosen first.
- **Sorting by time** — every list is passed through `sort_by_time`, so tasks
  read like a real day and unscheduled tasks sink to the bottom.
- **Conflict warnings** — `detect_conflicts` flags overlapping start times and
  the UI names the pets, the overlapping minutes, and a concrete fix.
- **Time-budget fit** — shrinking the slider drops the lowest-value tasks that
  no longer fit, which the report lists under "did not fit."

### Terminal demo (`main.py`)

For a no-UI run, `python main.py` builds a fixed owner/pet/task set (with
deliberately overlapping tasks) and prints today's schedule plus any conflicts:

```
========================================
Today's Schedule for Priya
========================================
  09:00  Morning walk     45 min  (high)
  09:30  Training         30 min  (medium)
    --  Nap              60 min  (low)
  09:15  Feed             10 min  (high)
  11:00  Laser play       20 min  (low)
----------------------------------------
  Total: 165 min
========================================

⚠️  2 time conflict(s) detected:
  - 'Morning walk' (09:00-09:45) overlaps 'Training' (starts 09:30)
  - 'Morning walk' (09:00-09:45) overlaps 'Feed' (starts 09:15)
```

> Note: the schedule lists tasks in **value order** (highest score first), which
> is why `Nap` (60 min) appears before the shorter `Feed`. The conflict check
> compares actual clock windows, so `Nap` — which has no start time — never
> conflicts.
