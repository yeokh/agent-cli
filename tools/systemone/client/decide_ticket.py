#!/usr/bin/env python3
"""Triage a support ticket via the local System One gateway.

Points Pydantic AI's SystemOneModel at http://127.0.0.1:8009 (or SYSTEM_ONE_BASE_URL).
The gateway forwards to OpenRouter / Kev / Ollama — the client never talks to them directly.
"""

from __future__ import annotations

import json
import os
import sys
from enum import Enum, IntEnum

from pydantic import BaseModel, ConfigDict

from pydantic_ai import Agent, UseEnumMemberDocstrings
from pydantic_ai.models.system_one import SystemOneModel
from pydantic_ai.providers.system_one import SystemOneProvider


class Department(UseEnumMemberDocstrings, str, Enum):
    returns = "returns"
    """Exchanges, refunds, wrong or damaged items."""

    shipping = "shipping"
    """Delivery status, delays, lost packages."""

    billing = "billing"
    """Charges, invoices, payment problems."""


class Frustration(UseEnumMemberDocstrings, IntEnum):
    calm = 0
    """Calm."""

    frustrated = 1
    """Frustrated."""

    very_angry = 2
    """Very angry."""


class TicketTriage(BaseModel):
    """Triage a customer support ticket."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    department: Department
    """Which team should handle this?"""

    escalate: bool
    """Does this need urgent human attention?"""

    frustration: Frustration
    """How frustrated is the customer?"""


DEFAULT_STATE = (
    "Shoes arrived two weeks late and in the wrong size. "
    "Also I see two charges on my card."
)


def build_agent() -> Agent[None, TicketTriage]:
    base_url = os.getenv("SYSTEM_ONE_BASE_URL", "http://127.0.0.1:8009")
    api_key = os.getenv("SYSTEM_ONE_API_KEY") or None
    model_name = os.getenv("SYSTEM_ONE_MODEL", "jev-latest")

    provider_kwargs: dict = {"base_url": base_url}
    if api_key:
        provider_kwargs["api_key"] = api_key

    model = SystemOneModel(
        model_name,
        provider=SystemOneProvider(**provider_kwargs),
    )
    return Agent(model, output_type=TicketTriage)


def main() -> int:
    state = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_STATE
    agent = build_agent()
    result = agent.run_sync(state)

    print("output:", result.output)
    details = result.response.provider_details
    if details:
        print("confidence:", json.dumps(details.get("confidence"), indent=2))
        print("probabilities:", json.dumps(details.get("probabilities"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
