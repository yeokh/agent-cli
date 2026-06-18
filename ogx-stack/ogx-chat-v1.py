from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8321/v1", api_key="fake")

response = client.responses.create(
    model="openai/qwen/qwen3-8b",
    # model="openai/anthropic/claude-haiku-4.5",
    input="Hi?",
)
print(response.output_text)
