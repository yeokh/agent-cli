import os
from openai import OpenAI

ogx_host = os.environ.get("OGX_HOST", "http://127.0.0.1:8321")
client = OpenAI(base_url=f"{ogx_host}/v1", api_key="fake")

MODEL = os.environ.get("OGX_MODEL", "openai/gpt-5-mini")

previous_response_id = None

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

    try:
        kwargs = dict(model=MODEL, input=qry)
        if previous_response_id:
            kwargs["previous_response_id"] = previous_response_id

        response = client.responses.create(**kwargs)
    except Exception as e:
        print(f"error: {e}")
        continue

    previous_response_id = response.id
    print(response.output_text)
