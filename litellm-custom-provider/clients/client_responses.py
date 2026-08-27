"""
OpenAI client -> LiteLLM proxy -> custom backend, via v1/responses, non-streaming.

LiteLLM bridges the Responses API to a chat-completions-style call under the
hood for providers (including custom ones) that don't natively speak the
Responses API, so this hits the same custom_handler.py as the chat.completions
examples -- only the client-facing shape differs.

Run the mock backend and the litellm proxy first (see README.md), then:
    python clients/client_responses.py
"""

from openai import OpenAI

client = OpenAI(base_url="http://localhost:4000", api_key="sk-1234")

response = client.responses.create(
    model="custom-llm-model",
    input="Say hello in three words.",
)

print("--- responses (non-streaming) ---")
print("output_text:", response.output_text)
print("status:", response.status)
print("usage:", response.usage)
