# PawPal+ Project Reflection

## 1. System Design

### a. Initial design

**Q: Briefly describe your initial UML design.**

A: My first UML (in `diagrams/uml.mmd`) was honestly more ambitious than what I
ended up building. It had eight classes: `Owner`, `Pet`, `Task`, `Schedule`, and
`Scheduler`, plus three helper value-objects — `TimeWindow` (a start/end time
range), `Preferences` (the owner's preferred and avoided time windows), and
`ScheduledItem` (a wrapper pairing a task with a concrete start/end and a "reason"
string for why it was chosen).

**Q: What classes did you include, and what responsibilities did you assign to
each?**

A:
- **`Owner`** — holds the person's name and their list of pets; add/remove/look up
  pets.
- **`Pet`** — id, name, species, age, and its list of care tasks.
- **`Task`** — one care task (name, duration, priority, recurring flag); knows how
  to score itself via `estimate_score`.
- **`Schedule`** — the chosen plan for a day; holds the selected tasks and totals
  their duration.
- **`Scheduler`** — the brains: builds the plan, ranks/sorts/filters tasks, and
  detects conflicts.
- **`TimeWindow` / `Preferences` / `ScheduledItem`** — originally meant to model
  time ranges, owner preferences, and "explained" schedule entries.

### b. Design changes

**Q: Did your design change during implementation?**

A: Yeah, quite a bit — it got simpler. I dropped `TimeWindow`, `Preferences`, and
`ScheduledItem` entirely, and my final code (`pawpal_system.py`) has just the five
core classes. I documented the corrected version in `diagrams/uml_final.mmd`.

**Q: If yes, describe at least one change and why you made it.**

A: The clearest one: I killed the `TimeWindow` class and replaced it with a plain
`start_time` string on `Task` (a zero-padded `"HH:MM"`). I realized I didn't
actually need a start/end object — a task already knows its `duration_minutes`, so
the end time is just `start + duration`, computed on the fly in
`check_time_overlap`. Collapsing it to a string also let `sort_by_time` sort
chronologically with plain string comparison instead of parsing datetimes.
Similarly, `ScheduledItem` disappeared because `Schedule` just holds `Task`
objects directly, and `Preferences` got cut because I decided time budget +
priority were enough constraints for this scenario.

## 2. Scheduling Logic and Tradeoffs

### a. Constraints and priorities

**Q: What constraints does your scheduler consider?**

A: Two main ones. **Time budget** — `generate_schedule` takes
`available_minutes` (default 480 = an 8-hour day) and won't schedule past it.
**Priority/value** — each task scores as `priority_weight × duration_minutes`
(low=1, medium=2, high=3) via `estimate_score`, and `rank_tasks_by_score` sorts
highest-value first. On top of those it tracks completion status (only incomplete
tasks get scheduled) and start-time conflicts (`detect_conflicts`).

**Q: How did you decide which constraints mattered most?**

A: I let the scenario drive it — a busy pet owner cares most about "did the
important stuff get done in the time I have?" So time budget is the hard limit and
priority is the tiebreaker for *what* fills that time. I deliberately left owner
"preferences" out (they were in my first UML) because they added complexity
without changing the core decision of which tasks make the cut.

### b. Tradeoffs

**Q: Describe one tradeoff your scheduler makes.**

A: It uses **greedy packing**, not optimal packing. `fit_tasks_in_time` walks the
value-ranked list and grabs each task that still fits the remaining budget — it
never backtracks to find the combination that maximizes total value. In my
`main.py` demo that means a 60-minute `Nap` gets picked ahead of a shorter `Feed`
purely because it scores higher, even though a smarter algorithm might have fit
two short tasks in the same space.

**Q: Why is that tradeoff reasonable for this scenario?**

A: Because it's O(n), predictable, and dead easy to explain — "I picked your
highest-value tasks until you ran out of time." For a daily pet-care planner
that's genuinely good enough, and a knapsack optimizer would be way more
complexity than the problem deserves. I also made the tradeoff transparent:
`get_scheduling_report` prints exactly which incomplete tasks "did not fit," so the
owner is never left guessing.

## 3. AI Collaboration

**Q: How did you use AI tools during this project?**

A: I used Claude Code across the whole thing, but split into four separate
sessions — classes, then tests, then the Streamlit UI, then docs. I mostly used it
for **code generation** (building each method), some **design brainstorming**
early on, and **refactoring** (like tightening `sort_by_time`). Keeping each
session single-purpose meant it wasn't juggling algorithm correctness and UI
polish at once, and each phase started from something I'd already verified.

**Q: What kinds of prompts or questions were most helpful?**

A: Two patterns. **Step-by-step expansion** — I built the scheduler one primitive
at a time (`estimate_score` → `rank_tasks_by_score` → `fit_tasks_in_time` →
`generate_schedule`) so each piece was small enough to actually read and check.
And **leading with concrete examples** — e.g. for conflict detection I gave the
exact case "09:00–09:45 should clash with 09:30–10:00, but a task ending exactly
at 09:30 should NOT clash with one starting at 09:30," which is why
`check_time_overlap` uses the half-open `start_a < end_b and start_b < end_a`. The
more I front-loaded my intent, the less I had to fix afterward.

### b. Judgment and verification

**Q: Describe one moment where you did not accept an AI suggestion as-is.**

A: For time sorting, Claude first wanted to parse every `start_time` with
`datetime.strptime` and sort on datetime objects. I rejected it because my
`_validate_time` already guarantees zero-padded fixed-width `"HH:MM"` strings — so
plain string comparison sorts chronologically already (`"09:30" < "10:00"`), no
parsing needed. I rewrote it to sort on a tuple key
`(task.start_time is None, task.start_time or "")`, which is lighter and also
pushes unscheduled tasks to the end instead of crashing on them.

**Q: How did you evaluate or verify what the AI suggested?**

A: Two ways. First, I checked it against invariants I'd set elsewhere — the
validation rule made the datetime parsing unnecessary. Second, I leaned hard on
tests: my suite has 117 passing tests, and behaviors like sorting order, conflict
detection, and recurrence each have dedicated cases, so anything the AI wrote had
to survive them before I trusted it.

## 4. Testing and Verification

**Q: What behaviors did you test?**

A: The core scheduling logic, spread across four files. `test_sort_filter.py`
covers `sort_by_time`, `filter_by_completion`, `filter_by_pet_name`, and
`start_time` validation. `test_conflicts_recurring.py` covers time-overlap /
conflict detection, `get_pet_schedule`, and recurring-task due-date logic.
`test_scheduler_plan.py` covers schedule generation and time-budget planning. And
`test_pawpal.py` covers validation and the Owner/Pet/Task basics. The three
headline behaviors — chronological sorting (unscheduled last), recurrence
roll-forward, and conflict detection — are each exercised end to end.

**Q: Why were these tests important?**

A: Because they're exactly the behaviors that are easy to get subtly wrong. The
half-open conflict interval (adjacent tasks *don't* clash) and the recurrence
roll-forward (completing a daily task advances `due_date` by `interval_days` and
reopens it) are the kind of edge logic where an off-by-one silently corrupts the
plan. Tests let me refactor — and let AI generate code — without fear.

### b. Confidence

**Q: How confident are you that your scheduler works correctly?**

A: Pretty confident for the cases I modeled — 117 tests pass and the tricky bits
(overlap boundaries, recurrence, unscheduled-task handling) all have explicit
coverage. I'd stop short of saying "provably correct," since greedy packing is
correct-by-design-choice, not optimal.

**Q: What edge cases would you test next if you had more time?**

A: Tasks that cross midnight (a start time near 23:30 with a long duration),
multiple recurring tasks colliding on the same future day, ties in
`estimate_score` (do equal-value tasks order stably?), and a zero-minute or
negative budget passed to `generate_schedule`. I'd also add a property-based test
that random task sets never produce a schedule exceeding the budget.

## 5. Reflection

**Q: What part of this project are you most satisfied with?**

A: The stateless `Scheduler` class. Keeping all the behavior in one place with no
stored state made everything downstream easier — `app.py` reuses a single
`scheduler` instance for sorting, filtering, and conflict checks, and every method
is trivially testable in isolation. It made the whole system feel clean.

**Q: If you had another iteration, what would you improve or redesign?**

A: I'd revisit greedy packing — probably offer an optional smarter fit that tries
to maximize the number of high-value tasks scheduled, not just grab them in score
order. I'd also bring back a lightweight version of the `Preferences` idea from my
original UML (preferred time windows), since that would make the plan feel more
personalized, and I'd let `main.py` print its schedule in time order to match the
Streamlit view.

**Q: What is one important thing you learned about designing systems or working
with AI on this project?**

A: That my real job was being the **architect**, not the typist. Claude Code is
fantastic at the "how" once I've pinned down the "what" and "why," so I trust it on
small, checkable pieces and boilerplate — but I override it whenever a decision
ripples through the system (greedy vs. optimal, the conflict interval, the
recurrence rule). A good prompt is basically a good spec: concrete examples, the
edge cases, and the invariants the code has to respect. The value I added wasn't
writing lines — it was deciding what "correct" meant and holding the AI to it.
