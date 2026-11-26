Explain each supplied SpreadsheetBench whole-task hard transition using its Parent/Candidate runs, effective Updates, mapped patches and actual diff. Keep the observed behavior change, its connection to an Update and the explanation of the score transition distinct.

## SpreadsheetBench event interpretation

Compare the task requirement, the actual submitted programs, execution records and supplied scoring for both sides. Identify which program produced the scored submission and preserve whether hard changed from 0 to 1 or 1 to 0. Describe all observable differences material to the explanation, including source and target selection, header and data boundaries, governing inputs, write locations, formula or value handling and recovery through actual feedback. Keep simultaneous changes visible even when only one matches the Update's intended behavior.

Read each relevant Update's conditions, action and strength with its actual patch in Parent context. Identify the visible change that corresponds to an implemented Update, then explain how far the evidence connects that change to the score transition. When several aspects changed together, state which aspect the Update addresses and what the other changes leave uncertain. Several visible changes can belong to one clearly connected correction. Assign an update_id when the evidence from both runs supports an explanation of how a distinguishable behavior change associated with that patch contributed to the whole-task gain or loss. If the patch explains a local change but the scored difference arose elsewhere, or the evidence leaves that connection unresolved, use null and describe the local change in text. If several patches could equally explain the transition or their effects cannot be distinguished, use null. An implementation detail may remain uncertain when the plausible paths support the same explanation of the transition. Apply the same reasoning to gains and losses, including regressions outside the Update's intended scope.

For each explanation, distinguish a path present in code, an action evidenced by the run, and a property of the saved output established by the supplied evidence. Check whether an exception handler, fallback or later save offers another route to the same score. A correct readable value can come from a formula cache or a static write. When both paths are plausible, describe the observable gain and the unresolved path. An input-workbook read does not verify the saved output; a clean exit does not show that repair or failure reporting was exercised. Apply the same discipline to source selection, target placement and ordinary transformations.

Use only the supplied preview, submitted programs, execution feedback, scores and comparison rules. Coordinate mismatches alone do not expose expected values or causes. Partial cell correctness may clarify a supplied hard transition. Check whether an unresolved detail could change the proposed explanation of the whole-task transition. Use null when that connection remains unresolved, and retain supported local observations in the Knowledge text. Record the evidential limit in the same Knowledge text so a later Preconditioner can use it without the original runs.

Write each Knowledge text as a concise, self-contained account of the relevant task condition, actual Parent/Candidate behavior difference, hard direction, supported Update connection or reason for null, and any material uncertainty. State the conditions supported by this event and the specific limits of the explanation. Keep the account useful to a future Preconditioner that receives Memory without this round's raw runs. Before returning, check the two sides, transition direction, simultaneous changes, patch implementation and the factual scope of each claim against this task's evidence.

In `text`, you may cite any Update in the current effective plan, including one with an empty patch. Only an Update with a nonempty patch is eligible for `update_id`.

## Exact output and multi-task example

Return one English JSON object with exactly `entries`. For N supplied flipped tasks, `entries` contains exactly one object, and that object contains exactly `knowledge`, an array of N events. Put every task's event in this single array. Each event has exactly `task_id`, `update_id` and nonempty `text`. Copy each supplied task ID exactly once. Include events with `update_id=null` in the same array. Before returning, check that the event task IDs match all supplied pairs, with each task appearing once.

Link to one nonempty implemented Update only when the paired evidence supports both its distinguishable behavioral connection and how that change contributed to the whole-task transition. If ambiguous, inseparable or unsupported use null and record what changed. Do not force attribution, split votes, predict Gate decisions or turn a joint execution into an independent causal claim. Cite only this task's current runs, diff and current effective IDs. If validation feedback is supplied, return the complete corrected object covering all supplied tasks.

The following hypothetical example illustrates two tasks in one `knowledge` array, including an attributed event and a null event. Use the actual supplied task IDs, effective Update IDs and evidence in your response. The number of events must match the number of supplied pairs. Return JSON without Markdown fences or surrounding commentary.

```json
{
  "entries": [
    {
      "knowledge": [
        {
          "task_id": "task-A",
          "update_id": "u1",
          "text": "The task requires a calculated total for every data row. Parent's submitted program stops before the last populated row, leaving its target cell blank, and scoring identifies that cell as the only mismatch. Candidate includes the last row with the same calculation and writes the total there, changing hard from 0 to 1. The implemented u1 patch directs the script to include the final data row. The changed loop boundary and removal of the sole mismatch support associating this gain with u1. This comparison covers the supplied workbook and does not independently measure the patch's isolated effect."
        },
        {
          "task_id": "task-B",
          "update_id": null,
          "text": "The task requires summing all source rows into a summary cell. Parent sums an incomplete range and the saved result fails scoring. Candidate corrects the sum range and also adds the post-save reopening check requested by u2, changing hard from 0 to 1. The execution record shows that the check passed without triggering a repair or another write. The u2 patch explains the added check, while the corrected calculation explains the changed submitted value. The supplied patches do not account for that range correction, so the evidence leaves the whole-task gain unassigned."
        }
      ]
    }
  ]
}
```
