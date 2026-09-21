"""
OpenAI client -> LiteLLM proxy -> custom backend, via v1/chat/completions, streaming.

Run the mock backend and the litellm proxy first (see README.md), then:
    python clients/client_chat_completions_stream.py
"""

from openai import OpenAI

client = OpenAI(base_url="http://localhost:4000", api_key="sk-1234")

stream = client.chat.completions.create(
    model="custom-llm-model",
    messages=[
        {"role": "system", "content": "You are a terse assistant."},
        {"role": "user", "content": "Say hello in three words."},
    ],
    stream=True,
)

print("--- chat.completions (streaming) ---")
for chunk in stream:
    delta = chunk.choices[0].delta if chunk.choices else None
    if delta and delta.content:
        print(delta.content, end="", flush=True)
print()
