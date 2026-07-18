import os
from openai import OpenAI

# Read OGX_HOST, fallback to default if not set
ogx_host = os.environ.get("OGX_HOST", "http://127.0.0.1:8321")

# Construct the base URL dynamically
client = OpenAI(base_url=f"{ogx_host}/v1", api_key="fake")

for model in client.models.list():
    print(model.id)


