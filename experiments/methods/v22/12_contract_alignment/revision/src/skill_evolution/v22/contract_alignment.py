"""Contract clarifications for the existing unified D/S/C update algorithm.

Only this profile changes the visible provenance/operation grammar and the learning
shape example. The behavioral rules, model output fields and compiler operations
remain those of unified_dsc; older profiles keep their original messages.
"""

from copy import deepcopy

from .compact_learning import SHAPE
from . import unified_dsc


PROFILE = "v22.unified_dsc.v3"
VIEW_SCHEMA = "v22.unified_dsc_view.v3"

GROUP_RULES = """
Frozen decision groups organize comparable choices, not separate Skills, independent
effects or permanent classes. requirement.basis is a flat list of source references:
cite actual current Parent events for each requirement. Group references record the
full provenance of those cited events, NOT the Update's applicability. The program
adds missing current group references using the frozen event-to-group map; any group
you explicitly cite must have supporting Parent events in the same basis. State the
Update's applicable conditions and scope in requirement.text, not by selecting a main
source group. Transfer depends on decision meaning, conditions, actual edits and
Parent/capability dependencies, not group identity. Coordinate across groups; retain
side effects and unassessed scope. In history, basis.actual_update_ref resolves through
historical_updates; historical_sources entries with actual_update_ref/path use that
shared snapshot. These are historical evidence, never current events. Do not hard-code
group IDs or emit certification tables.
"""

# Replace the existing operation paragraphs; do not stack another instruction list.
FUSION_RULES = unified_dsc.FUSION_RULES.replace(
    "Emit only increments in the shown shape. Each from names existing requirements, each\n"
    "at most once. replace requires nonempty to with COMPLETE retained obligations,",
    "Emit only increments in the shown shape. changes.from is a nonempty list of\n"
    "existing requirement IDs; each may be changed at most once. replace requires\n"
    "nonempty to with COMPLETE retained obligations,",
).replace(
    "Every watch affected by changed requirements needs an explicit nonempty destination in\n"
    "watch_changes; retain important adverse/preservation questions, moving to intent when\n"
    "appropriate. New requirements need a watch destination or blocking open. from=[] adds a\n"
    "question. Original open persists; add only actual blockers. Cite current source keys or\n"
    "unchanged Memory IDs. Use existing reason fields, without extra audit or D/S/C fields.",
    "Every watch affected by changed requirements needs an explicit nonempty destination in\n"
    "watch_changes.to. Retain important adverse/preservation questions; watch.about names\n"
    "active requirement IDs or intent, so about=[\"intent\"] can retain a goal-level question\n"
    "after withdrawal. Only watch_changes.from=[] adds a new question. Every transformed\n"
    "requirement needs a watch destination or blocking open. Original open persists; add\n"
    "only actual blockers as {\"about\":[\"active requirement ID, Watch ID, or intent\"],\n"
    "\"reason\":\"concrete unresolved blocker\"}. These IDs refer to the effective Plan.\n"
    "Cite current source keys or unchanged Memory IDs. Use existing reason fields,\n"
    "without extra audit or D/S/C fields.",
)

# This is an append example: a nonempty retirement requires an Effect in replace.
# LEARNING_RULES already specifies the retirement record when revision is warranted.
EFFECTIVE_SHAPE = deepcopy(SHAPE)
EFFECTIVE_SHAPE["memory_delta"][0]["retire_limits"] = []
