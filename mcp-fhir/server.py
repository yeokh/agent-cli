"""MCP server exposing read-only search/fetch access to a FHIR REST API.

Defaults to HAPI's public R4 test server (https://hapi.fhir.org/baseR4).
Override with the FHIR_BASE_URL env var to point at a different FHIR server
(e.g. HAPI's R5 or DSTU2 test endpoints).
"""

import os
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

FHIR_BASE_URL = os.environ.get("FHIR_BASE_URL", "https://hapi.fhir.org/baseR4").rstrip("/")

# Starter allow-list of resource types. Widen this (or drop the check) once
# you're comfortable with how the server behaves against the test server.
SUPPORTED_RESOURCE_TYPES = {
    "Patient",
    "Practitioner",
    "Organization",
    "Encounter",
    "Condition",
    "Observation",
    "Procedure",
    "MedicationRequest",
    "AllergyIntolerance",
    "DiagnosticReport",
}

mcp = MCPServer("fhir")

_client = httpx.AsyncClient(
    base_url=FHIR_BASE_URL,
    headers={"Accept": "application/fhir+json"},
    timeout=30.0,
)


def _check_resource_type(resource_type: str) -> str | None:
    if resource_type not in SUPPORTED_RESOURCE_TYPES:
        return (
            f"Unsupported resource type '{resource_type}'. "
            f"Supported types: {', '.join(sorted(SUPPORTED_RESOURCE_TYPES))}"
        )
    return None


def _summarize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    resource = entry.get("resource", {})
    return {
        "id": resource.get("id"),
        "resourceType": resource.get("resourceType"),
        "resource": resource,
    }


@mcp.tool()
async def list_supported_resource_types() -> list[str]:
    """List the FHIR resource types this server currently supports."""
    return sorted(SUPPORTED_RESOURCE_TYPES)


@mcp.tool()
async def search_fhir(
    resource_type: str,
    query: dict[str, str] | None = None,
    count: int = 10,
) -> dict[str, Any]:
    """Search for FHIR resources of a given type on the test server.

    Args:
        resource_type: FHIR resource type, e.g. "Patient" or "Observation".
            See list_supported_resource_types for the current allow-list.
        query: FHIR search parameters as a flat dict, e.g.
            {"name": "Smith", "birthdate": "1990-01-01"} or
            {"patient": "123", "code": "http://loinc.org|29463-7"}.
        count: Max number of results to return (default 10, capped at 50).
    """
    error = _check_resource_type(resource_type)
    if error:
        return {"error": error}

    params = dict(query or {})
    params["_count"] = str(min(count, 50))

    try:
        response = await _client.get(f"/{resource_type}", params=params)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return {"error": f"FHIR server returned {exc.response.status_code}", "detail": exc.response.text[:2000]}
    except httpx.HTTPError as exc:
        return {"error": f"Request to FHIR server failed: {exc}"}

    bundle = response.json()
    entries = bundle.get("entry", [])
    return {
        "total": bundle.get("total"),
        "returned": len(entries),
        "results": [_summarize_entry(e) for e in entries],
    }


@mcp.tool()
async def read_fhir(resource_type: str, resource_id: str) -> dict[str, Any]:
    """Fetch a single FHIR resource by type and id from the test server.

    Args:
        resource_type: FHIR resource type, e.g. "Patient".
        resource_id: The resource's logical id (not its full URL).
    """
    error = _check_resource_type(resource_type)
    if error:
        return {"error": error}

    try:
        response = await _client.get(f"/{resource_type}/{resource_id}")
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return {"error": f"FHIR server returned {exc.response.status_code}", "detail": exc.response.text[:2000]}
    except httpx.HTTPError as exc:
        return {"error": f"Request to FHIR server failed: {exc}"}

    return response.json()


if __name__ == "__main__":
    mcp.run()
