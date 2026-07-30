import os
from openai import OpenAI

# Read OGX_HOST, fallback to default if not set
ogx_host = os.environ.get("OGX_HOST", "http://127.0.0.1:8321")

# Construct the base URL dynamically
client = OpenAI(base_url=f"{ogx_host}/v1", api_key="fake")

#MODEL = "anthropic/claude-haiku-4.5"
#MODEL = "openai/gpt-5-nano"
MODEL = os.environ.get("OGX_MODEL", "openai/gpt-5-mini")


history = []

while True:
    try:
        qry = input("you: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        break

    if not qry:
        continue

    if qry in ("/exit", "/quit"):
        break

    history.append({"role": "user", "content": qry})

    try:
        response = client.chat.completions.create(model=MODEL, messages=history)
    except Exception as e:
        print(f"error: {e}")
        history.pop()
        continue

    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})
    print(reply)
