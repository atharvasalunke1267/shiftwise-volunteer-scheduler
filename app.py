"""Local Streamlit interface for the ShiftWise volunteer scheduler."""

from __future__ import annotations

import csv
import importlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import streamlit as st


ROOT = Path(__file__).resolve().parent
SCENARIO_PATHS = {
    "Normal staffing": ROOT / "data" / "normal_staffing.json",
    "Limited staffing": ROOT / "data" / "limited_staffing.json",
}
SOLVER_MODULES = {
    "OR-Tools": "shiftwise.solver_ortools",
    "PuLP": "shiftwise.solver_pulp",
}


@st.cache_data
def load_scenario(path_string: str) -> dict[str, Any]:
    with Path(path_string).open(encoding="utf-8") as scenario_file:
        scenario = json.load(scenario_file)
    validate_scenario(scenario)
    return scenario


def validate_scenario(scenario: dict[str, Any]) -> None:
    """Catch malformed bundled data before calling a solver."""
    for key in ("scenario_id", "label", "volunteers", "slots"):
        if key not in scenario:
            raise ValueError(f"Scenario is missing required field {key!r}.")

    volunteers = scenario["volunteers"]
    slots = scenario["slots"]
    if not isinstance(volunteers, list) or not isinstance(slots, list):
        raise ValueError("Scenario volunteers and slots must be lists.")
    if not slots:
        raise ValueError("A demo scenario must contain at least one slot.")

    slot_ids = [slot.get("id") for slot in slots]
    if any(not isinstance(slot_id, str) or not slot_id for slot_id in slot_ids):
        raise ValueError("Every slot must have a nonempty string ID.")
    if len(set(slot_ids)) != len(slot_ids):
        raise ValueError("Slot IDs must be unique within a scenario.")
    known_slot_ids = set(slot_ids)

    volunteer_ids: list[str] = []
    for volunteer in volunteers:
        required = {
            "id", "name", "skills", "available_slot_ids",
            "max_assignments", "preferred_slot_ids",
        }
        missing = required - volunteer.keys()
        if missing:
            raise ValueError(f"Volunteer record is missing: {', '.join(sorted(missing))}.")
        if not isinstance(volunteer["id"], str) or not volunteer["id"]:
            raise ValueError("Every volunteer must have a nonempty string ID.")
        volunteer_ids.append(volunteer["id"])
        cap = volunteer["max_assignments"]
        if isinstance(cap, bool) or not isinstance(cap, int) or cap < 0:
            raise ValueError(f"Volunteer {volunteer['id']} must have a nonnegative integer assignment cap.")
        for field in ("skills", "available_slot_ids", "preferred_slot_ids"):
            if not isinstance(volunteer[field], list):
                raise ValueError(f"Volunteer {volunteer['id']} field {field!r} must be a list.")
        for field in ("available_slot_ids", "preferred_slot_ids"):
            unknown = set(volunteer[field]) - known_slot_ids
            if unknown:
                raise ValueError(
                    f"Volunteer {volunteer['id']} field {field!r} references unknown slots: "
                    f"{', '.join(sorted(unknown))}."
                )
    if len(set(volunteer_ids)) != len(volunteer_ids):
        raise ValueError("Volunteer IDs must be unique within a scenario.")

    for slot in slots:
        required = {"id", "role", "start_time", "end_time", "required_skill"}
        missing = required - slot.keys()
        if missing:
            raise ValueError(f"Slot record is missing: {', '.join(sorted(missing))}.")
        start, end = slot["start_time"], slot["end_time"]
        if (
            isinstance(start, bool) or not isinstance(start, int)
            or isinstance(end, bool) or not isinstance(end, int)
            or end <= start
        ):
            raise ValueError(f"Slot {slot['id']} must have integer times with end_time > start_time.")
        skill = slot["required_skill"]
        if skill is not None and (not isinstance(skill, str) or not skill.strip()):
            raise ValueError(f"Slot {slot['id']} required_skill must be a nonempty string or null.")


def to_contract_records(scenario: dict[str, Any]) -> tuple[list[SimpleNamespace], list[SimpleNamespace]]:
    """Adapt JSON records to the documented attribute-based solver contract.

    The shared dataclasses are not present yet. SimpleNamespace keeps the
    documented field names and can be replaced by Manas's types at integration.
    """
    volunteers = [
        SimpleNamespace(
            id=row["id"],
            name=row["name"],
            skills=set(row["skills"]),
            available_slot_ids=set(row["available_slot_ids"]),
            max_assignments=row["max_assignments"],
            preferred_slot_ids=set(row["preferred_slot_ids"]),
        )
        for row in scenario["volunteers"]
    ]
    slots = [SimpleNamespace(**row) for row in scenario["slots"]]
    return volunteers, slots


def read_result_field(result: Any, field: str) -> Any:
    if isinstance(result, dict):
        return result[field]
    return getattr(result, field)


def format_time(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def result_rows(scenario: dict[str, Any], result: Any, solver_name: str) -> list[dict[str, str]]:
    volunteers = {v["id"]: v for v in scenario["volunteers"]}
    slots = {slot["id"]: slot for slot in scenario["slots"]}
    assignments = read_result_field(result, "assignments")
    assigned_by_slot: dict[str, str] = {}
    for volunteer_id, slot_id in assignments:
        if slot_id in assigned_by_slot:
            raise ValueError(f"Solver returned more than one assignment for slot {slot_id}.")
        if volunteer_id not in volunteers or slot_id not in slots:
            raise ValueError("Solver returned an assignment with an unknown volunteer or slot ID.")
        assigned_by_slot[slot_id] = volunteer_id

    rows: list[dict[str, str]] = []
    for slot in scenario["slots"]:
        volunteer_id = assigned_by_slot.get(slot["id"], "")
        volunteer_name = volunteers[volunteer_id]["name"] if volunteer_id else ""
        rows.append({
            "Solver": solver_name,
            "Slot": slot["id"],
            "Role": slot["role"],
            "Time": f"{format_time(slot['start_time'])}–{format_time(slot['end_time'])}",
            "Required skill": slot["required_skill"] or "None",
            "Volunteer": volunteer_name,
            "Volunteer ID": volunteer_id,
        })
    return rows


def render_solver_result(scenario: dict[str, Any], result: Any, solver_name: str) -> list[dict[str, str]]:
    assignments = read_result_field(result, "assignments")
    status = read_result_field(result, "status")
    filled = read_result_field(result, "filled_slots")
    total = read_result_field(result, "total_slots")
    preferences = read_result_field(result, "preference_count")
    elapsed = read_result_field(result, "elapsed_seconds")
    rows = result_rows(scenario, result, solver_name)

    st.subheader(f"{solver_name} roster")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Coverage", f"{filled}/{total}")
    percentage = (filled / total * 100) if total else 0.0
    col2.metric("Coverage rate", f"{percentage:.1f}%")
    col3.metric("Preference matches", str(preferences))
    col4.metric("Solver time", f"{elapsed:.4f} s")
    st.caption(f"Status: {status}")

    display_rows = [{key: value for key, value in row.items() if key != "Solver"} for row in rows]
    st.dataframe(display_rows, use_container_width=True, hide_index=True)
    uncovered = [row["Slot"] for row in rows if not row["Volunteer"]]
    if uncovered:
        st.warning("Uncovered slots: " + ", ".join(uncovered))
    else:
        st.success("All slots are covered.")

    counts = {v["id"]: 0 for v in scenario["volunteers"]}
    for volunteer_id, _slot_id in assignments:
        if volunteer_id in counts:
            counts[volunteer_id] += 1
    st.markdown("**Assignments per volunteer**")
    count_rows = [
        {"Volunteer": v["name"], "Assignments": counts[v["id"]], "Limit": v["max_assignments"]}
        for v in scenario["volunteers"]
    ]
    st.dataframe(count_rows, use_container_width=True, hide_index=True)
    return rows


def csv_bytes(rows: list[dict[str, str]]) -> bytes:
    output = io.StringIO(newline="")
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def load_solver(name: str):
    module = importlib.import_module(SOLVER_MODULES[name])
    return module.solve


def run_solvers(scenario: dict[str, Any], selected_solver: str) -> dict[str, Any]:
    volunteers, slots = to_contract_records(scenario)
    solver_names = list(SOLVER_MODULES) if selected_solver == "Compare both" else [selected_solver]
    results: dict[str, Any] = {}
    for solver_name in solver_names:
        solve = load_solver(solver_name)
        results[solver_name] = solve(volunteers, slots)
    return results


def main() -> None:
    st.set_page_config(page_title="ShiftWise", page_icon="🗓️", layout="wide")
    st.title("ShiftWise: Volunteer Shift Scheduler")
    st.write("Build a coverage-first volunteer roster for a fictional Campus Tech Fest.")

    scenario_label = st.selectbox("Staffing scenario", list(SCENARIO_PATHS))
    solver_choice = st.selectbox("Solver", ["OR-Tools", "PuLP", "Compare both"])
    try:
        scenario = load_scenario(str(SCENARIO_PATHS[scenario_label]))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        st.error(f"Could not load this scenario: {error}")
        return

    st.caption(scenario["description"])
    st.write(f"**{len(scenario['volunteers'])} volunteers · {len(scenario['slots'])} slots**")

    if st.button("Run optimization", type="primary"):
        try:
            st.session_state["last_results"] = run_solvers(scenario, solver_choice)
            st.session_state["last_scenario_id"] = scenario["scenario_id"]
            st.session_state["last_solver_choice"] = solver_choice
        except ModuleNotFoundError as error:
            missing = error.name or "a required module"
            st.error(
                f"{missing} is not available yet. The selected solver module or its dependency "
                "must be added before optimization can run. Scenario data is loaded and validated."
            )
        except (AttributeError, KeyError, TypeError, ValueError, RuntimeError) as error:
            st.error(f"Optimization could not be completed: {error}")

    results = st.session_state.get("last_results", {})
    if st.session_state.get("last_scenario_id") != scenario["scenario_id"]:
        results = {}
    if results:
        all_csv_rows: list[dict[str, str]] = []
        comparison_rows = []
        if len(results) == 2:
            st.subheader("Solver comparison")
            for solver_name, result in results.items():
                comparison_rows.append({
                    "Solver": solver_name,
                    "Status": read_result_field(result, "status"),
                    "Filled slots": f"{read_result_field(result, 'filled_slots')}/{read_result_field(result, 'total_slots')}",
                    "Preference matches": read_result_field(result, "preference_count"),
                    "Elapsed seconds": read_result_field(result, "elapsed_seconds"),
                })
            st.dataframe(comparison_rows, use_container_width=True, hide_index=True)
            columns = st.columns(2)
            for column, (solver_name, result) in zip(columns, results.items()):
                with column:
                    all_csv_rows.extend(render_solver_result(scenario, result, solver_name))
        else:
            solver_name, result = next(iter(results.items()))
            all_csv_rows = render_solver_result(scenario, result, solver_name)
        st.download_button(
            "Download roster as CSV",
            data=csv_bytes(all_csv_rows),
            file_name=f"{scenario['scenario_id']}_roster.csv",
            mime="text/csv",
        )

    with st.expander("About this model"):
        st.write(
            "The solver selects eligible volunteer-to-slot edges. Availability, skills, "
            "overlapping times, and assignment limits are hard constraints. It maximizes "
            "coverage first and preference matches second."
        )


if __name__ == "__main__":
    main()
