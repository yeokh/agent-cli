# https://strandsagents.com/docs/user-guide/sdk/quickstart/python/
uv init
uv add openai strands-agents[anthropic]

vi agent.py
export OPENAI_API_KEY="your-api-key"
uv run agent.py "Explain yourself"

## Arguments

| Flag | Long form | Description | Default |
|------|-----------|-------------|---------|
| `-p` | `--prompt` | Prompt text (or pass as positional arg) | *(required)* |
| `-w` | `--working-folder` | Read/write working directory | `.` (current dir) |
| `-i` | `--input-folder` | Read-only input directory | *(none)* |
| `-o` | `--output-folder` | Read/write output directory for generated files | working folder |

## Execution Examples

```bash
uv run agent.py "What is an agent harness, in one sentence?"
uv run agent.py -p "Summarize file structure in working folder"
uv run agent.py -p "Analyze data in working folder" -w ./workspace
uv run agent.py -p "Process records from input and save summary" -w ./workspace -i ./input
uv run agent.py -p "Generate a report from the input files" -w ./workspace -i ./input -o ./output
uv run agent.py -p "Process the files from the working folder based on the instruction in the input folder" \
                -w /root/agent-jobs/ascii-jpeg-art/input \
                -i /root/agent-jobs/ascii-jpeg-art/agent \
                -o /root/agent-jobs/ascii-jpeg-art/output

uv run agent.py -p "Please read your job instruction in the input folder and generate the ansible playbook based on the request form in the working folder: pb-2026-002.txt" \
                -w /root/agent-jobs/ansible-playbook-builder/input \
                -i /root/agent-jobs/ansible-playbook-builder/agent \
                -o /root/agent-jobs/ansible-playbook-builder/output

```

> **Note:** If `-o` is omitted, generated output is written to the working folder (`-w`).
