# fhir-mcp-server

A minimal MCP server that lets an LLM search and read resources from a FHIR
test server (defaults to HAPI's public R4 sandbox at
`https://hapi.fhir.org/baseR4`, see https://hapi.fhir.org/about).

Read-only, no auth required — HAPI's public test servers accept anonymous
reads. Data on them is public, ephemeral test data; don't put real PHI in it,
and don't rely on any resource still being there next week.

## Tools

- `list_supported_resource_types()` — the current allow-list of resource types.
- `search_fhir(resource_type, query, count)` — FHIR search, e.g.
  `search_fhir("Patient", {"family": "Smith"})` or
  `search_fhir("Observation", {"patient": "137202485", "code": "http://loinc.org|29463-7"})`.
- `read_fhir(resource_type, resource_id)` — fetch one resource by id.

Supported resource types (edit `SUPPORTED_RESOURCE_TYPES` in `server.py` to
change): Patient, Practitioner, Organization, Encounter, Condition,
Observation, Procedure, MedicationRequest, AllergyIntolerance,
DiagnosticReport.

## Setup

```bash
uv sync
```

## Run it directly

```bash
uv run python server.py
```

## Try it with the MCP inspector

```bash
uv run mcp dev server.py
```

## Wire it into Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fhir": {
      "command": "uv",
      "args": ["--directory", "C:\\DevWorks\\fhir-mcp-server", "run", "python", "server.py"]
    }
  }
}
```

## Pointing at a different FHIR server

Set `FHIR_BASE_URL`, e.g. to HAPI's R5 test endpoint:

```bash
FHIR_BASE_URL=https://hapi.fhir.org/baseR5 uv run python server.py
```

## Notes

- Uses `mcp` SDK v2.x, where the server class is `MCPServer`
  (`mcp.server.mcpserver`), not the `FastMCP` class shown in most v1-era
  tutorials — those two are API-compatible for `@mcp.tool()` but import from
  different modules.
- Next steps once this is solid: pagination (`_getpages`/next links from the
  search Bundle), narrowing `_summarize_entry` per resource type instead of
  echoing the full resource, and — only if you actually need it — write
  tools (`create_fhir`/`update_fhir`) gated behind an explicit confirmation
  step, since the test server is a shared public sandbox.
