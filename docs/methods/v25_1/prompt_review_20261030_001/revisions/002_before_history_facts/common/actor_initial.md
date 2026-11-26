# Instruction
{{instruction}}{{task_metadata}}

# Input spreadsheet preview
{{workbook_preview}}

# Task
Write a Python script that reads the workbook from `INPUT_PATH`, applies the instruction, and writes the modified workbook to `OUTPUT_PATH`. Preserve all other cells unchanged. The preview may be truncated — do not hardcode row counts or assume the data ends at the last previewed row; iterate over all actual rows in the workbook instead. Return only a ```python``` code block.