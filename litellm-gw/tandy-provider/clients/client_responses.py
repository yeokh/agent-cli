"""
OpenAI client -> LiteLLM proxy -> Tandy backend, via v1/responses, non-streaming.

LiteLLM automatically bridges the Responses API to the same underlying
completion() call — no extra config needed.

Start the Tandy backend and the LiteLLM proxy first (see README.md), then:
    python clients/client_responses.py
"""

from openai import OpenAI

client = OpenAI(base_url="http://localhost:4000", api_key="sk-1234")

response = client.responses.create(
    model="gpt-5-mini",
    input="Give me a 1-sentence health tip.",
)

print("--- responses (non-streaming) ---")
print("output_text:", response.output_text)
