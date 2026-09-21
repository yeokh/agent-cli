"""
OpenAI client -> LiteLLM proxy -> Tandy backend, via v1/chat/completions, non-streaming.

Start the Tandy backend and the LiteLLM proxy first (see README.md), then:
    python clients/client_chat_completions.py
"""

from openai import OpenAI

client = OpenAI(base_url="http://localhost:4000", api_key="sk-1234")

response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[
        {"role": "system", "content": "You are a helpful health assistant."},
        {"role": "user", "content": "Give me a 1-sentence health tip."},
    ],
)

print("--- chat.completions (non-streaming) ---")
print("content     :", response.choices[0].message.content)
print("finish_reason:", response.choices[0].finish_reason)
print("usage       :", response.usage)
