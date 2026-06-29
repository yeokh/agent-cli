from openai import OpenAI

# openai_url = "http://127.0.0.1:8321/v1"
openai_url = "https://distribution-starter-route-aa-ogx-stack.apps.ocp.b7785.sandbox5220.opentlc.com/v1"
client = OpenAI(base_url=openai_url, api_key="fake")

# MODEL = "openai/anthropic/claude-haiku-4.5"
MODEL = "openai/openai/gpt-5-nano"
# MODEL = "openai/openai/gpt-4o-mini"

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
