# ShiftWise dataset specification

This document gives Darshan the dataset design checklist for the project in [PROJECT_BRIEF.md](../PROJECT_BRIEF.md). The brief is the source of truth for the objective and constraints.

## Ownership and scope

**Darshan alone authors the actual synthetic records**, chooses their values, defines the scenarios, and documents dataset assumptions. No other member creates or revises the synthetic records. Manas implements general validation against the frozen contract and does not need to approve or prepare the data before other work begins.

Use fictional names and a fictional Campus Tech Fest. A sensible initial target is 10–12 volunteers and 8–12 individual role slots across several periods; tune these suggested values if needed to keep the app and explanation manageable. These are planning values, not final records. Do not place actual final volunteer records in this specification.

## Data schema

The eventual records should load into the Python contract below. A JSON or similarly readable format is suitable; the final file format is Darshan's choice as long as the app can load both scenarios consistently.

### Volunteer

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Unique stable volunteer identifier within the scenario. |
| `name` | string | Fictional display name for the roster. |
| `skills` | set/list of strings | Skills the volunteer can use, such as a technical or event skill. |
| `available_slot_ids` | set/list of strings | Slot IDs for which the volunteer is available. |
| `max_assignments` | integer | Maximum number of slots the volunteer may cover during the event. |
| `preferred_slot_ids` | set/list of strings | Slots the volunteer would prefer, whether or not they are ultimately assigned. |

### Shift slot

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Unique identifier for one position, including repeated positions. |
| `role` | string | Human-readable event role. |
| `start_time` | integer | Minutes after midnight on the event day. |
| `end_time` | integer | Minutes after midnight; must be greater than `start_time`. |
| `required_skill` | string or `null` | Required skill, or `null` when no special skill is required. |

Represent each position separately. For example, two people needed for a role become two slot records with distinct IDs. Use one time basis throughout the event. Intervals are half-open: `[start_time, end_time)`. Slots overlap if `start1 < end2` and `start2 < end1`, so adjacent slots may be served back-to-back.

The scenario data should also have a clear top-level scenario identifier and display label, but those fields are scenario metadata rather than volunteer or slot fields. The solver receives the volunteer and slot collections.

## Required scenarios

1. **Normal staffing:** provide sufficient eligible, non-conflicting capacity to fill most or all slots. The scenario should let the team show that it can find a high-coverage roster.
2. **Limited staffing:** make at least one position impossible to fill in a valid full roster because of skill scarcity, availability, overlapping times, or a combination. The model must return a partial roster and identify the uncovered position, not fail.

The scenarios may share many records or may be independently authored. Keep the reason for the limited scenario's shortage explainable in one or two sentences during the demo.

## Design checklist: required demonstrations

Across the scenarios, deliberately include each of these cases:

- **Availability:** at least one volunteer is unavailable for a particular slot, making that pair ineligible.
- **Skill:** at least one slot requires a skill; include both a volunteer who meets it and at least one otherwise plausible volunteer who does not.
- **Satisfied preference:** at least one preferred volunteer-slot pair is selected in an optimal roster.
- **Preference sacrificed for coverage:** create a case where choosing a preferred assignment would reduce total filled slots. The coverage-first objective must choose the higher-coverage roster even though it earns fewer preference points.
- **Overlap:** at least two slot intervals overlap. Ensure that assigning one volunteer to both is forbidden, while separate volunteers can cover both when eligible.
- **Binding assignment cap:** at least one volunteer has a cap that affects which set of positions they can cover; demonstrate that the model cannot exceed it.
- **Shortage:** the limited-staffing scenario has at least one unfilled slot in an optimal roster.
- **Detectable invalid data:** document representative invalid or contradictory records for validation to reject, without putting invalid records into the normal demo input. Examples include duplicate IDs, a reference to an unknown slot, an end time not after start time, a negative cap, or a preference referring to a nonexistent slot.

Do not make every volunteer available for every slot or every role skill-free. The data should stay readable while making meaningful eligible and ineligible edges visible.

## Quality rules and useful assumptions

- IDs are stable, unique, and easy to read aloud; names and event details are fictional.
- Every availability and preference ID refers to a slot in the same scenario.
- Skill labels use a consistent spelling and capitalization convention.
- Skills, availability, and preferences contain no duplicate values after normalization.
- Assignment limits are nonnegative integers. A zero cap is allowed only if useful to the scenario and explained.
- Each slot has a positive duration and uses the same event-day minute scale.
- Each multi-person role is expanded into individual slots with distinct IDs and the same relevant time/skill values.
- A no-special-skill slot uses an explicit `null`/empty representation consistently, rather than a made-up skill label.
- Each scenario has enough context for the coordinator to understand its staffing conditions.
- Keep demo scenario size modest enough that the roster and trade-offs can be inspected by hand.

## How Darshan checks the dataset

1. **Trace a few assignments by hand.** For selected slots, list the volunteers who are available and meet the required skill. Confirm that the solver's choices are among those candidates.
2. **Check exclusions.** Pick an unavailable volunteer-slot pair and a skill-mismatch pair and confirm neither appears as an eligible edge or returned assignment.
3. **Check conflicts and caps.** Trace the schedule of a capped volunteer and a volunteer facing overlapping candidate slots. Confirm the intended trade-off changes the attainable roster.
4. **Check preferences.** Verify at least one preference can be satisfied in a maximum-coverage roster and that a different preference is sacrificed when keeping it would lower coverage.
5. **Check both scenarios.** Confirm the normal case fills most or all positions and the limited case has at least one unavoidable uncovered slot. Explain why the slot is scarce using the eligibility and conflict facts.
6. **Check validation cases.** Keep malformed examples out of the normal files and verify the shared validation rules can identify each documented defect clearly.
7. **Check solver comparison.** Compare filled count and preference count. Multiple equally optimal assignment lists are acceptable.

## Validation checklist for the implementation

The general validator should report actionable errors before solver invocation. It should check:

- Required fields and expected types are present.
- Volunteer IDs are unique; slot IDs are unique.
- Names, IDs, roles, and skill labels are nonempty strings where required.
- Availability and preference references point to known slot IDs.
- Caps are integers greater than or equal to zero.
- Times are integer minutes and `end_time > start_time`.
- A required skill is either `null` or a nonempty string.
- Scenario inputs have at least one slot for a normal demo run.
- No duplicate or contradictory IDs/references appear after collection normalization.

The validator does not decide whether a scenario has enough staff or whether a preference trade-off is effective; those are dataset quality checks Darshan documents and traces.
