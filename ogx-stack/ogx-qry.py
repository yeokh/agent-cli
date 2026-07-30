import os
from openai import OpenAI

# Read OGX_HOST, fallback to default if not set
ogx_host = os.environ.get("OGX_HOST", "http://127.0.0.1:8321")
ogx_model = os.environ.get("OGX_MODEL", "openai/gpt-5-mini")

# Construct the base URL dynamically
client = OpenAI(base_url=f"{ogx_host}/v1", api_key="fake")

qry="Hi?"
print("you:", qry)

response = client.chat.completions.create(
    model=ogx_model,
    messages=[{"role": "user", "content": qry}],
)

print(response.choices[0].message.content)
