"""Inherited pure grouping contracts; no Prompt or model transport is loaded."""
import re
from ..facts import require
from ..benchmark import current as benchmark_current

def references(value):
    """Resolve explicit references and common numeric ranges without altering prose."""
    refs = set(re.findall(r"\bP\d+(?::[A-Za-z0-9_]+)?\b", value))
    for match in re.finditer(r"\b(P\d+):(\d+)\s*[-–—]\s*(?:(P\d+):)?(\d+)\b", value):
        prefix, start, end_prefix, end = match.groups()
        require(end_prefix in (None, prefix), "Cross-execution step range")
        start, end = int(start), int(end)
        require(0 <= start <= end <= 10000, "Invalid step range")
        refs.update(f"{prefix}:{i}" for i in range(start, end + 1))
    return refs

def validate_grouping(*args, **kwargs):
    return benchmark_current().evidence("contracts.grouping.validate_grouping", *args, **kwargs)

def candidate_groups(saved, task_ids):
    """Reuse Parent membership by paired task identity; never inspect Candidate outcomes."""
    source_by_ref = {source["ref"]: source["task_id"] for source in saved["sources"]}
    by_task = {source_by_ref[member]: group["group_id"]
               for group in saved["grouping"]["groups"] for member in group["members"]}
    require(len(task_ids) == len(set(task_ids)) and set(task_ids) <= set(by_task),
            "Unknown or duplicate Candidate task")
    return {task: by_task[task] for task in task_ids}
