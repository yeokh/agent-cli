"""
OpenAI client -> LiteLLM proxy -> Tandy backend, via v1/responses, streaming.

Start the Tandy backend and the LiteLLM proxy first (see README.md), then:
    python clients/client_responses_stream.py
"""

from openai import OpenAI

client = OpenAI(base_url="http://localhost:4000", api_key="sk-1234")

print("--- responses (streaming) ---")
with client.responses.stream(
    model="gpt-5-mini",
    input="Give me a 1-sentence health tip.",
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
print()
