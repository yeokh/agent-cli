#!/usr/bin/env python3
"""Decision via local System One gateway; chat fallback via OpenRouter.

- Primary model: SystemOneModel → local gateway (SYSTEM_ONE_BASE_URL)
- Fallback model: OpenRouter chat (OPENROUTER_API_KEY) — a different endpoint

When the decision model cannot fill a route (e.g. free-form reply text) or the
upstream System One call fails, FallbackModel hands the step to the chat LLM.
"""

from __future__ import annotations

import os
import sys
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict

from pydantic_ai import Agent, UseEnumMemberDocstrings
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.models.system_one import SystemOneModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.providers.system_one import SystemOneProvider


class Department(UseEnumMemberDocstrings, str, Enum):
    returns = "returns"
    """Exchanges, refunds, wrong or damaged items."""

    shipping = "shipping"
    """Delivery status, delays, lost packages."""

    billing = "billing"
    """Charges, invoices, payment problems."""


class TicketTriage(BaseModel):
    """Route a problem to the team that owns it."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    department: Department
    """Which team should handle this?"""

    escalate: bool
    """Does this need urgent human attention?"""


class CustomerReply(BaseModel):
    """Answer the customer in plain language (requires a language model)."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    body: str
    """The reply to send to the customer."""

    tone: Literal["empathetic", "neutral", "formal"]
    """Tone of the reply."""


DEFAULT_STATE = (
    "Shoes arrived two weeks late and in the wrong size. "
    "Also I see two charges on my card. Please tell me what you will do."
)


def build_agent() -> Agent[None, TicketTriage | CustomerReply]:
    system_one_base = os.getenv("SYSTEM_ONE_BASE_URL", "http://127.0.0.1:8009")
    system_one_key = os.getenv("SYSTEM_ONE_API_KEY") or None
    system_one_model = os.getenv("SYSTEM_ONE_MODEL", "jev-latest")

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        raise SystemExit(
            "OPENROUTER_API_KEY is required for the chat fallback provider."
        )
    chat_model_name = os.getenv("OPENROUTER_CHAT_MODEL", "openai/gpt-4o-mini")

    provider_kwargs: dict = {"base_url": system_one_base}
    if system_one_key:
        provider_kwargs["api_key"] = system_one_key

    decision = SystemOneModel(
        system_one_model,
        provider=SystemOneProvider(**provider_kwargs),
    )
    chat = OpenRouterModel(
        chat_model_name,
        provider=OpenRouterProvider(api_key=openrouter_key),
    )

    # Decision model first; chat LLM on API errors or unfillable routes (str fields).
    model = FallbackModel(decision, chat, fallback_on=(ModelAPIError,))
    return Agent(
        model,
        output_type=[TicketTriage, CustomerReply],
        instructions=(
            "If the customer needs a written reply, produce CustomerReply. "
            "Otherwise triage with TicketTriage."
        ),
    )


def main() -> int:
    state = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_STATE
    agent = build_agent()
    result = agent.run_sync(state)

    print("model used:", result.response.model_name)
    print("output type:", type(result.output).__name__)
    print("output:", result.output)
    details = result.response.provider_details
    if details:
        print("provider_details keys:", sorted(details.keys()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
