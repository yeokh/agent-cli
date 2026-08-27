"""
OpenAI client -> LiteLLM proxy -> custom backend, via v1/chat/completions, non-streaming.

Run the mock backend and the litellm proxy first (see README.md), then:
    python clients/client_chat_completions.py
"""

from openai import OpenAI

client = OpenAI(base_url="http://localhost:4000", api_key="sk-1234")

response = client.chat.completions.create(
    model="custom-llm-model",
    messages=[
        {"role": "system", "content": "You are a terse assistant."},
        {"role": "user", "content": "Say hello in three words."},
    ],
)

print("--- chat.completions (non-streaming) ---")
print("content:", response.choices[0].message.content)
print("finish_reason:", response.choices[0].finish_reason)
print("usage:", response.usage)
