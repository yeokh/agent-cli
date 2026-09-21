"""
OpenAI client -> LiteLLM proxy -> custom backend, via v1/responses, streaming.

Run the mock backend and the litellm proxy first (see README.md), then:
    python clients/client_responses_stream.py
"""

from openai import OpenAI

client = OpenAI(base_url="http://localhost:4000", api_key="sk-1234")

stream = client.responses.create(
    model="custom-llm-model",
    input="Say hello in three words.",
    stream=True,
)

print("--- responses (streaming) ---")
for event in stream:
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
    elif event.type == "response.completed":
        print()
        print("final status:", event.response.status)
        print("usage:", event.response.usage)
