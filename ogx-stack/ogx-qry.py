from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8321/v1", api_key="fake")

qry="Hi?"
print("you:", qry)

response = client.responses.create(
    # model="openai/gpt-4o-mini",
    model="openai/qwen/qwen3-8b",
    input=qry,
)

print(response.output_text)
