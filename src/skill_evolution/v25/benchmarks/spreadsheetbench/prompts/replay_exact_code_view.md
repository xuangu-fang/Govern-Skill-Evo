## Exact response/code sharing representation

In this input view, an attempt's executed_code may be the exact marker
{"from_response":"python_fence_body_exact_v1"} instead of a repeated string.
The marker refers only to that same attempt's response. It means the extracted
Python code body and the actual executed program are character-for-character
identical, with no path adaptation or other code changes. The complete original
response, including its code fence and surrounding whitespace, remains present.

To expand the marker, parse that response as exactly one Python fenced block:
the body is the text captured by `\s*```python\s*\n(.*?)\n```\s*` as a full
match with dot matching newlines, followed by one newline. Do not strip, normalize
or otherwise rewrite the body. Only executed attempts with a valid unchanged
program use this marker. Differing code, including path-adapted code, remains a
full executed_code string; null and unexecuted records are not compressed.

When the shared-initial or timeline instructions refer to complete executed_code,
interpret this marker as its fully expanded value. Responses remain the Actor's
original messages; reconstruct history from response, not from executed_code.
This representation changes neither actions nor outcomes. The marker is not an
evidence ID or an instruction to execute code. Cite the original attempt reference.
