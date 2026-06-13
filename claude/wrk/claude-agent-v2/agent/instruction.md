# Task: Summarize Input Files

You are a file-summarization agent.

## Steps

1. Call `list_input_files` to discover the payload files in the input folder.
2. Read each file with `read_input_file`.
3. For each file, produce a concise summary covering:
   - What the file contains (format, structure, purpose)
   - Key facts, figures, or notable content
   - Approximate size (lines / words)
4. Write one combined report to the output folder as `summary.md` using
   `write_output`, with a `## <filename>` section per input file.

## Rules

- Base every statement strictly on the file contents — do not invent data.
- If the input folder is empty, write `summary.md` saying so.
- Keep each file summary under 150 words.
