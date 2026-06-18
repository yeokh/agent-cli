from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8321/v1", api_key="fake")
# MODEL = "openai/anthropic/claude-haiku-4.5"
MODEL = "openai/qwen/qwen3-8b"

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

    kwargs = {"model": MODEL, "input": qry}
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    try:
        response = client.responses.create(**kwargs)
    except Exception as e:
        print(f"error: {e}")
        continue

    previous_response_id = response.id
    print(response.output_text)
