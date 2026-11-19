# Synthetic scenario notes

Darshan authored these fictional Campus Tech Fest scenarios. The records are demonstration data, not real people. Both scenarios use 11 volunteers and 10 individual slots. Slot times are minutes after midnight, and intervals use the half-open convention from the project brief.

## Scenarios

- `normal_staffing.json` gives AV-skilled volunteers availability for setup and demo support. Each slot has at least one eligible volunteer, and the chosen availabilities allow all ten slots to be staffed without violating caps or overlaps.
- `limited_staffing.json` removes every AV-skilled volunteer's availability for `av-setup`. That slot requires AV, so its eligible set is empty and it must remain uncovered; the other AV role, `av-demo`, still has an eligible volunteer.

## Deliberate model demonstrations

- **Availability exclusion:** for example, V04 is available only for `registration-1`; V04 cannot be assigned to `registration-2`.
- **Required skills:** `av-setup` and `av-demo` require `AV`; `photo-booth` requires `Photo`. A volunteer without the matching skill is ineligible even if their availability includes the slot.
- **Preference satisfied:** preferences include `photo-booth` for V07 and `info-desk` for V09, which can be satisfied in a maximum-coverage roster.
- **Preference sacrificed for coverage:** V01 prefers `av-demo` and is the only volunteer available for `workshop-checkin`. V02 can cover `av-demo` but cannot cover check-in. Assigning V02 to demo and V01 to check-in covers both overlapping slots; assigning V01 to the preferred demo slot leaves check-in open. Coverage must win.
- **Overlap:** `av-setup` overlaps the 09:00–10:00 registration slots and the 10:00–11:00 help-desk/photo slots. `av-demo` and `workshop-checkin` both run 11:00–12:00. A volunteer cannot cover two overlapping positions.
- **Binding assignment cap:** V03 is available for four positions, prefers both registration slots, and has `max_assignments: 1`. It can cover at most one of those preferences; other volunteers must cover the other slot. This limits its preference contribution and prevents assigning V03 to multiple positions.
- **Shortage:** limited staffing has no eligible AV-skilled volunteer for `av-setup`, so the position is necessarily unfilled.
- **Invalid records for validation checks:** keep malformed samples out of these scenario files. Useful validation examples include a duplicate slot ID, a preference or availability reference to an unknown slot, an end time equal to its start time, a negative assignment cap, or a non-string required skill.

## Manual trace notes

In normal staffing, one full-coverage feasibility trace is: V04 covers `registration-1`, V03 covers `registration-2`, V05 covers `helpdesk-1`, V07 covers `helpdesk-2`, V10 covers `av-setup`, V02 covers `av-demo`, V01 covers `workshop-checkin`, V09 covers `info-desk`, V08 covers `cleanup`, and V11 covers `photo-booth`. This trace respects the listed caps and assigns no volunteer to overlapping slots. It is a feasibility witness, not a claim that every solver will return this exact roster.

For the preference-versus-coverage trace, V01 is eligible for both `av-demo` and `workshop-checkin`, while V02 is eligible only for `av-demo`. The two slots overlap. Selecting V01 for the preferred `av-demo` prevents V01 from covering check-in, and no other volunteer is available for check-in. Assigning V02 to demo and V01 to check-in fills both.

For the V03 cap, without the cap V03 could cover both registration slots and gain both of its listed preference matches. With the cap, it can cover at most one; V04 is an alternative for `registration-1`, while V05 or V09 can cover `registration-2`. This makes the cap relevant while retaining a full-coverage normal roster.
