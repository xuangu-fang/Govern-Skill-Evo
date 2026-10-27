import re
from src.skill_evolution.v24.facts import require, text
from src.skill_evolution.v24.contracts.grouping import references

def validate_grouping(result, facts):
    require(isinstance(result, dict) and set(result) == {"groups"}, "Expected only groups")
    groups = result["groups"]
    require(isinstance(groups, list) and bool(groups), "Expected nonempty groups")
    runs = {run["ref"]: run for run in facts["runs"]}
    allowed = set(runs)
    for ref, run in runs.items():
        allowed.update({f"{ref}:0", f"{ref}:outcome"})
        allowed.update(event["step"] for event in run["steps"])
    group_ids, assigned = set(), []
    fields = {"group_id", "members", "decision_problem", "shared_basis", "important_differences"}
    for group in groups:
        require(isinstance(group, dict) and set(group) == fields, "Expected exactly five group fields")
        group_id = text(group["group_id"], "group_id")
        require(group_id not in group_ids, "Duplicate group_id")
        group_ids.add(group_id)
        members = group["members"]
        require(isinstance(members, list) and bool(members)
                and all(isinstance(x, str) and x in runs for x in members), "Invalid members")
        assigned.extend(members)
        text(group["decision_problem"], "decision_problem")
        basis = text(group["shared_basis"], "shared_basis")
        differences = group["important_differences"]
        require(isinstance(differences, list), "important_differences must be an array")
        for difference in differences:
            text(difference, "important_difference")
        for prose in [group["decision_problem"], basis, *differences]:
            require(references(prose) <= allowed, "Unresolvable execution/step reference")
            menu_refs = set(re.findall(r"\bC\d+\b", prose))
            require(menu_refs <= set(facts["command_sets"]), "Unresolvable command-set reference")
        basis_refs = references(basis)
        for member in members:
            events = {event["step"] for event in runs[member]["steps"]}
            if not events:
                events = {f"{member}:0"}
            require(bool(events & basis_refs), f"shared_basis lacks a decision-step reference for {member}")
    require(len(assigned) == len(set(assigned)) and set(assigned) == set(runs),
            "Members must cover every execution exactly once")
    for group in groups:
        for prose in [group["decision_problem"], group["shared_basis"], *group["important_differences"]]:
            require(set(re.findall(r"\bG\d+\b", prose)) <= group_ids, "Unresolvable group reference")
    return result
