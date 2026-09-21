"""
OpenAI client -> LiteLLM proxy -> Tandy backend, via v1/chat/completions, streaming.

Start the Tandy backend and the LiteLLM proxy first (see README.md), then:
    python clients/client_chat_completions_stream.py
"""

from openai import OpenAI

client = OpenAI(base_url="http://localhost:4000", api_key="sk-1234")

stream = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[
        {"role": "system", "content": "You are a helpful health assistant."},
        {"role": "user", "content": "Give me a 1-sentence health tip."},
    ],
    stream=True,
)

print("--- chat.completions (streaming) ---")
for chunk in stream:
    delta = chunk.choices[0].delta if chunk.choices else None
    if delta and delta.content:
        print(delta.content, end="", flush=True)
print()
