# Runtime feedback
category: {{error_category}}
exit_status: {{exit_status}}

{{error_detail_prefix}}

detail_truncated: {{detail_truncated}}
code_attempts_used: {{code_attempts_used}}
code_attempts_remaining: {{code_attempts_remaining}}

Correct the reported format, execution or output-file error and return one complete
Python script in a single python fenced block. The next execution starts from the
original input in a fresh directory, without any previous attempt's files or state.
This message contains runtime information, not a correctness evaluation.
