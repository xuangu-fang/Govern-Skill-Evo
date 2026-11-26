Transform each Original Update into an effective correction for the current SpreadsheetBench Parent through Direction, Scope and Coordination (D/S/C). Use Parent to judge existing coverage and instruction interactions, and use relevant Memory and current execution evidence to adjust direction, applicability, strength and preservation boundaries.

## SpreadsheetBench domain guidance

Use these concepts to examine the supplied evidence. Select the aspects relevant to the task and keep competing explanations open when the records are insufficient. Express the findings through your existing output contract.

- Workbook structure and intent. Distinguish source tables from destinations, locate the header and data boundaries, identify the intended write region, and consider governing inputs such as a year, control or filter criterion. Example or reference tabs in the original input may clarify the transformation. Follow the requested operation and preserve valid content outside its scope.
- Failure explanations. Consider missing coverage (rule_missing), a misleading existing rule (rule_wrong), a visible program that departs from relevant guidance (rule_ignored), insufficient workbook reading or selection (data_exploration), a program defect (code_error), and unresolved or other causes (other). A rule_ignored hypothesis requires comparing actual code with the applicable rule. Existing feedback can handle an isolated syntax or API error. A Skill revision requires current evidence for a transferable behavioral correction, including when a recurring API misconception is involved. Category names are optional analytical vocabulary within ordinary prose.
- Successful behavior. Look for evidence of useful data localization (effective_exploration), behavior consistent with applicable guidance (applied_rule), or a reusable recovery following an observed format, execution or invalid-output error (iterative_recovery). A successful output alone leaves the role of the Skill uncertain. Source code shows intended operations, while execution records determine which behavior is observable. Private reasoning remains outside the supplied evidence.
- Reusable implementation knowledge. API names, argument patterns and short illustrative code can express behavior that transfers across workbooks. For example, ws.append() appends rows, whereas explicit cell assignment locates writes in a specified region. Match the choice to whether the task calls for appending records or overwriting a known region, preserving legitimate uses of both. This example illustrates the distinction. Support proposed changes with the current runs and use Memory only within your module's permissions.
- Generalization. Express the operation and its usable conditions. Remove case IDs, one-off sheet names, fixed coordinates, answer values and local paths from the proposed Skill guidance. Keep evaluation field names and thresholds in analysis. Preserve reusable library behavior and any necessary task conditions when simplifying the wording.

## Preconditioner use

The complete Parent describes the current Skill. Original Plan supplies the proposed problems and corrections, cited runs supply current execution evidence, and Memory reports historical edits and responses. Work within each Original's problem and existing ID. The current runs may be only the cited subset of the batch, while Parent is supplied in full.

Read all relevant Parent guidance, including conditions and exceptions in other paragraphs. Determine what is already covered, which behavior needs to change, and where the proposal overlaps or conflicts with existing guidance. When execution fails despite a relevant rule, consider whether its trigger, action, strength, priority or interaction needs correction. Repetition or stronger wording requires a supported behavioral reason.

Relate relevant Memory to the proposed behavior and its applicable conditions. Compare the reported edit, observed response and preservation boundaries with the present workbook operation. Keep improvements, regressions and uncertainty in view. When a similar intervention previously failed to help or caused a relevant regression, consider what materially differs in the current proposal or setting. A different workbook name alone provides little basis for expecting a different response. With empty or irrelevant Memory, judge the Original from Parent and the current evidence.

Use the visible code, actual execution feedback and available scoring to distinguish a missing opportunity, a visible departure from guidance, and behavior that occurred without the expected improvement. Source code alone may leave branch execution uncertain. Historical raw workbooks and trajectories are outside the supplied Memory view. Keep mixed historical outcomes and their conditions together when adjusting a current proposal.

## Direction, Scope and Coordination

Make one integrated judgment before choosing an action. These dimensions guide the decision and its explanation in the existing fields.

D — Direction. Determine which behavior should be encouraged, changed or discontinued for the Original problem. Relevant historical support or counterexamples may redirect the proposal. Evaluate the proposed replacement on its own supporting evidence as well.

S — Scope. State the task-visible triggers, instruction strength, exceptions and useful branches supported by current evidence and relevant history. In SpreadsheetBench, these can include appending versus overwriting, data versus headers or summaries, the requested target region, and formula or value requirements. Treat new priorities, ordering, thresholds and stopping conditions as behavioral choices. Keep protections tied to the supported correction and actual program capabilities.

C — Coordination. Decide how the correction fits the relevant Parent rules and other surviving Originals. Identify affected old guidance by recognizable wording or behavior, then state what to replace, qualify, consolidate or remove and which valid branches remain. Resolve conflicting old conditions in the effective correction. Consolidate related repetition within the Original's scope when it helps express the intended behavior clearly, and allow new guidance when the correction requires it.

Review the intended combined behavior of Parent and all surviving Updates. Make overlapping conditions and necessary priorities explicit in effective text. Preserve IDs and each proposal's problem boundary. Each surviving correction must be complete even if another Update is deferred. Resolve necessary dependencies within the existing proposals, or withdraw affected proposals when a supported complete correction cannot be expressed.

## Complete effective adjustments

KEEP when the Original already specifies a reasonable correction in this Parent, including its behavior, conditions, strength, necessary old-rule treatment and interactions. Use REPLACE when an exception, priority or change to existing guidance is needed, putting the entire effective requirement in text. Editor receives that text and has no access to your reason, cited runs or Memory. Keep the decisive evidence and uncertainty in reason. Use WITHDRAW when the proposal is unwarranted, redundant or cannot form a supported correction within its problem boundary. Assess validity from the available evidence even when Memory is empty. Preserve task requirements and useful behavior on primary and fallback paths.

Return JSON only: {"adjustments":[{"target":"u1","action":"KEEP","text":null,"reason":"..."}]}. Exactly one action per Original ID. KEEP when already sufficient. REPLACE supplies complete changed text, not a diff. WITHDRAW when unwarranted or redundant. KEEP and WITHDRAW have null text. All may be withdrawn.
