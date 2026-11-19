# ShiftWise: Volunteer Shift Scheduler

## Project overview

ShiftWise is a small local application for a campus club or event coordinator. It assigns volunteers to individual role slots using volunteer skills, slot availability, shift times, assignment limits, and preferences. The goal is to fill as many positions as possible while honoring every hard constraint. When full coverage is impossible, the app presents a usable partial roster and clearly identifies unfilled slots.

The project demonstrates **combinatorics, bipartite matching, and constraints** through deterministic optimization. The running application will not call a generative AI service or require an AI API key. AI tools may be used by the team while developing or reviewing the project.

The sample event is a fictional Campus Tech Fest. The prototype should be reusable for another event by changing its input data, while staying small enough to finish under a short course deadline.

## User and recurring use case

The primary user is a campus club or event coordinator who needs to prepare a roster for an event with multiple roles and time periods. They select a staffing scenario and solver, run the optimizer, review the roster and uncovered positions, compare solver scores when requested, and download the roster as CSV. The same workflow should work for another event represented in the agreed data format.

## MVP scope and non-goals

### MVP

- A local Streamlit application with normal-staffing and limited-staffing scenarios.
- Two implementations of the same model: OR-Tools CP-SAT and PuLP.
- A common input and result contract for both solvers.
- A roster, uncovered-slot list, coverage metrics, preference count, per-volunteer assignment counts, and an optional side-by-side solver comparison.
- CSV download of the displayed roster.
- Fictional, synthetic data designed to exercise the constraints and objective.
- Input validation and a short repeatable demo.

### Non-goals for the first version

Custom CSV uploads, accounts, persistent database storage, online deployment, notifications, and advanced styling are stretch work only after the MVP and both solvers work. The prototype does not need a generative AI feature or service.

## Discrete mathematics concepts

Represent volunteers as vertices on the left side of a bipartite graph and individual role slots as vertices on the right. Add an edge between volunteer `v` and slot `s` only if `v` is available for `s` and has the required skill, if any. A selected edge means that volunteer is assigned to that slot. The selected edges form a matching-like assignment: each slot can have at most one selected edge, while volunteers may serve multiple non-overlapping slots up to their assignment limit. Thus this is a constrained bipartite assignment model rather than a plain one-to-one matching problem.

This graph representation is combinatorial: the optimizer chooses a subset of eligible edges. Binary decision variables encode those choices, and constraints rule out combinations that violate the event rules.

## Dataset ownership and specification

**Darshan alone owns dataset design and authorship.** This includes choosing the synthetic records, creating both scenarios, documenting assumptions, and checking that examples exercise the requirements. No other member is assigned to create, revise, or approve the synthetic records. Manas's validation code will consume the agreed data contract and does not make him a data prerequisite.

The recommended initial size is about **10–12 volunteers and 8–12 individual role slots**, distributed across several time periods. These are starting values to tune if the model or demo needs to be smaller. A position requiring multiple people is represented by separate slots with unique IDs, such as `registration-1` and `registration-2`.

Each volunteer record has a unique ID, display name, skill set, IDs of available slots, maximum number of assignments for the event, and preferred slot IDs. Each slot record has a unique ID, role, start and end time, and a required skill or an explicit no-special-skill value. The detailed schema and design checklist are in [docs/DATASET_SPEC.md](docs/DATASET_SPEC.md). No final volunteer records are specified in this brief.

The dataset must include two scenarios:

- **Normal staffing:** enough compatible availability to fill most or all slots.
- **Limited staffing:** scarcity in availability, skill, or non-overlapping time combinations leaves at least one slot unfilled.

Across these scenarios, demonstrate unavailability, a skill requirement, a satisfiable preference, a preference that must be sacrificed to preserve coverage, overlapping slots, a binding assignment limit, and invalid or contradictory records that validation can detect. Darshan should manually trace selected eligible and ineligible pairs and verify that scarce or overlapping cases affect the resulting roster.

## Mathematical model

Let `V` be the volunteers, `S` the complete set of role slots, and `E` the eligible volunteer-slot pairs. Define a binary variable `x(v,s)` only for `(v,s)` in `E`:

- `x(v,s) = 1` when volunteer `v` is assigned to slot `s`.
- `x(v,s) = 0` otherwise.

Let `P` be the eligible pairs where the slot is preferred by that volunteer. Use the coverage-first objective:

```text
maximize (|S| + 1) * sum(x(v,s) for (v,s) in E)
       + sum(x(v,s) for (v,s) in P)
```

The preference sum is at most `|S|`, because each slot can have at most one assigned volunteer. Gaining one filled slot therefore adds `|S| + 1`, which is more than the maximum possible loss of `|S|` preference points. Coverage always has priority; preferences break ties between maximum-coverage rosters.

Subject to:

1. **At most one volunteer per slot:** for each `s`, `sum(x(v,s) for eligible v) <= 1`.
2. **Assignment limit:** for each `v`, `sum(x(v,s) for eligible s) <= max_assignments(v)`.
3. **No overlap for a volunteer:** for every volunteer `v` and pair of distinct slots `s1`, `s2` whose time intervals overlap, `x(v,s1) + x(v,s2) <= 1` when both variables exist.
4. **Eligibility:** variables exist only for pairs that satisfy availability and skill requirements. Ineligible pairs cannot be selected.
5. **Partial coverage is allowed:** the slot constraint is an upper bound, not an equality. If full coverage is impossible, the optimizer can leave positions open and report them.

Use half-open intervals `[start_time, end_time)` for overlap checks. Two slots overlap when `start1 < end2` and `start2 < end1`; one ending exactly when another begins does not overlap.

Availability, required skills, overlap, and assignment limits are **hard constraints**. Preferences are not feasibility requirements; they contribute only secondary objective points. If a solver cannot return an optimal result within its configured limit but has a feasible incumbent, the normalized status should say `feasible` and the result should still include that incumbent.

## Solver requirements and shared contract

The project must contain two separate implementations of this exact model: OR-Tools CP-SAT and PuLP. Both accept the same volunteer and slot objects and return a common result. They should agree on optimal coverage and preference score, while the particular volunteer selected for a slot may differ when multiple rosters have the same objective value.

Freeze the following interface before solver and app integration begins. Times are integer minutes after midnight on the same event day, making comparisons straightforward. Collections may be represented as Python `set[str]` or `list[str]`; normalize them to sets for membership checks.

```text
Volunteer:
  id: str
  name: str
  skills: set[str] | list[str]
  available_slot_ids: set[str] | list[str]
  max_assignments: int
  preferred_slot_ids: set[str] | list[str]

ShiftSlot:
  id: str
  role: str
  start_time: int       # minutes after midnight
  end_time: int         # minutes after midnight; must be > start_time
  required_skill: str | None

SolverResult:
  status: str           # normalized: "optimal", "feasible", or "no_solution"
  assignments: list[tuple[str, str]]  # (volunteer_id, slot_id)
  filled_slots: int
  total_slots: int
  preference_count: int
  elapsed_seconds: float
```

Both modules expose `solve(volunteers, slots) -> SolverResult`. Each assignment pair appears at most once; returned pairs must refer to known, eligible records. `no_solution` is a defensive normalized value for backend errors or no usable incumbent; the zero-assignment solution is mathematically feasible for valid input. Validation errors should be surfaced before calling a solver rather than silently converted to an empty roster. `elapsed_seconds` measures the solver call, not app rendering. The app computes coverage percentage as `filled_slots / total_slots * 100`, with a safe display for zero slots even though a valid scenario is expected to contain slots.

PuLP requires a working optimization backend such as CBC or another supported solver. The team must specify installation and verify that PuLP can actually solve a small model in the target development environment before the presentation. See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the dependency and integration sequence.

## Prototype feature requirements

The local Streamlit interface should provide:

- A scenario selector for normal and limited staffing.
- A solver selector: OR-Tools, PuLP, or compare both.
- A clear run/optimize action.
- A roster table with slot, role, time, assigned volunteer, and relevant required-skill information.
- A clear list of uncovered slots.
- Filled/total coverage and percentage, preference matches, and assignment count per volunteer.
- A comparison view for both solvers showing coverage, preferences, status, and elapsed time. It must not imply that volunteer-by-volunteer identity must match.
- A button to download the roster as CSV.

## Success criteria and demo expectations

The project is ready for its demonstration when:

- Both solvers run on the same validated scenarios using the frozen contract.
- Hard constraints hold in every returned assignment and unfilled slots are reported.
- Both solvers optimize coverage first and preferences second; the comparison shows their scores without requiring identical rosters.
- Normal staffing fills most or all positions, and limited staffing visibly leaves at least one position open.
- The interface exposes the requested roster and metrics and can download CSV.
- Each member can explain their owned contribution and the team can explain the graph, variables, objective, and constraints.
- The team has confirmed the PuLP backend works on the presentation environment.

The short flow and viva guidance are in [docs/DEMO_AND_VIVA.md](docs/DEMO_AND_VIVA.md). Member responsibilities and the integration checklist are in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).
