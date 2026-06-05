# Exercise 06 — Multi-Agent Pipeline

**Track:** Advanced | **Time:** ~40 min

---

## Objective

Chain multiple Claude Agent SDK calls in `web_app.py` to build a pipeline where
each stage uses a different model and handles a focused step. This mirrors
multi-agent patterns used in production AI systems.

---

## Background

### Why pipeline instead of one agent?

A single agent handling everything has limits:

- Long tasks accumulate context, increasing cost and reducing reliability.
- Different steps suit different models: cheap/fast for extraction, capable for reasoning.
- A specialist agent with a focused system prompt is more reliable than a generalist.

A **pipeline** splits the work into stages:

```
┌─────────────────┐   temp dir   ┌─────────────────┐   outbox
│   Agent Stage 1  │ ────────────▶│  Agent Stage 2   │ ────────▶ results
│  fast model      │              │  capable model   │
│  (extract data)  │              │  (write report)  │
└─────────────────┘               └─────────────────┘
```

In `web_app.py`, each stage calls `claude_agent.run_agent()` with a different
`model_key`, `inbox`, and `outbox`. The output directory of one stage becomes
the input of the next.

---

## Steps

### 1. Add `_pipeline_thread()` to `web_app.py`

Find the `# WORKSHOP PLACEHOLDER (Exercise 06 — Multi-Agent Pipeline)` comment
in `web_app.py` and replace it with:

```python
import tempfile  # add to imports at top of file if not already present

def _pipeline_thread() -> None:
    """
    Two-stage pipeline thread.
      Stage 1 (fast model)    — extract structured data from inbox → JSON in temp dir
      Stage 2 (capable model) — read JSON, write final Markdown report to outbox
    """
    state.start()
    state.add_log("=== Pipeline started ===")

    log_path = OUTBOX_DIR / "agent.log"
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="claude-stage1-") as stage1_dir:
        stage1_out = Path(stage1_dir)

        with log_path.open("w", encoding="utf-8") as log_fh:
            def _log(message: str) -> None:
                if message:
                    state.add_log(message)
                    log_fh.write(message + "\\n")
                    log_fh.flush()

            # ── Stage 1: Extract ──────────────────────────────────────────────
            state.add_log("-" * 60)
            state.add_log("Stage 1/2 — Extracting structured data (fast model)...")

            fast_model = (
                "haiku" if os.environ.get("ANTHROPIC_API_KEY") else state.model
            )

            try:
                claude_agent.run_agent(
                    model_key=fast_model,
                    inbox=INBOX_DIR,
                    outbox=stage1_out,
                    log_callback=_log,
                )
            except Exception as exc:
                state.finish(f"Stage 1 failed: {exc}")
                return

            _log("-" * 60)
            _log("Stage 1 complete. Intermediate files:")
            for p in sorted(stage1_out.iterdir()):
                _log(f"  {p.name}  ({p.stat().st_size} bytes)")

            # ── Stage 2: Analyze ─────────────────────────────────────────────
            _log("-" * 60)
            _log(f"Stage 2/2 — Analyzing data and writing report ({state.model})...")

            try:
                claude_agent.run_agent(
                    model_key=state.model,
                    inbox=stage1_out,
                    outbox=OUTBOX_DIR,
                    log_callback=_log,
                )
            except Exception as exc:
                state.finish(f"Stage 2 failed: {exc}")
                return

    state.finish()
    state.add_log("=== Pipeline completed successfully ===")
```

### 2. Add the pipeline API route

After `api_run_agent()` in `web_app.py`, add:

```python
@app.route("/api/agent/pipeline", methods=["POST"])
def api_run_pipeline():
    """Start the two-stage pipeline in a background thread."""
    if state.status == "running":
        return jsonify({"error": "Agent is already running"}), 409
    if not (INBOX_DIR / "instruction.md").exists():
        return jsonify({"error": "instruction.md not found in inbox"}), 400
    if not claude_agent.get_available_models():
        return jsonify({"error": "No API key configured"}), 400

    thread = threading.Thread(target=_pipeline_thread, daemon=True, name="pipeline")
    thread.start()
    return jsonify({"status": "started", "stages": 2})
```

### 3. Write two-stage instructions

The pipeline needs two instructions — one per stage. Upload both to the inbox.

**inbox/instruction.md** (used by Stage 1 — extraction):
```markdown
# Stage 1: Data Extraction

Read all CSV files in the inbox. For each file:
1. Parse every row into a JSON object.
2. Write the objects as a JSON array to the outbox using the original filename
   with a .json extension (e.g. sample_data.csv → sample_data.json).
3. Also write a schema file: <name>_schema.json listing column names and
   the data type you infer for each (string, number, or boolean).

Do not summarize or analyze the data — only extract.
Write outbox/agent.log with a one-line entry per file processed.
```

**inbox/stage2_instruction.md** (swap in for second run manually):
```markdown
# Stage 2: Analysis and Report

Read all .json files in the inbox. These were extracted from CSV files.

Produce a single Markdown report at outbox/report.md with:
  ## Executive Summary   (2–3 sentences on key findings)
  ## Department Analysis (table: department, headcount, avg salary)
  ## Top Earners         (top 3 by salary with name, dept, salary, location)
  ## Conclusion          (one sentence)

Also write outbox/stats.json with:
  total_employees, average_salary, department_count, top_earner_name
```

### 4. Run the pipeline

Restart `web_app.py`, then trigger the pipeline from the terminal:

```bash
curl -X POST http://localhost:8080/api/agent/pipeline
```

Watch the browser log stream. You should see:

```
=== Pipeline started ===
------------------------------------------------------------
Stage 1/2 — Extracting structured data (fast model)...
model=haiku  inbox=…/inbox  outbox=…/claude-stage1-…
[tool_use] Read(file_path='…/sample_data.csv')
[tool_use] Write(file_path='sample_data.json', …)
------------------------------------------------------------
Stage 1 complete. Intermediate files:
  sample_data.json  (1842 bytes)
------------------------------------------------------------
Stage 2/2 — Analyzing data and writing report (...)
```

---

## Reflection questions

1. Stage 1 uses a fast, cheap model and stage 2 uses the selected model. What
   would break if you swapped them? What determines the right model per stage?

2. Stage 1's output goes into a temp directory that is deleted after the `with`
   block. If the pipeline crashes partway through stage 2, you cannot inspect
   stage 1's intermediate files. How would you improve observability?

3. How does this pipeline compare to a single long-running agent call?

---

## Key takeaways

- The Claude Agent SDK makes multi-stage pipelines easy: call `run_agent()` more
  than once with different inputs.
- Use cheap models for extraction steps and capable models for analysis steps.
- Logging both stages into `agent.log` makes it easy to audit the pipeline.
