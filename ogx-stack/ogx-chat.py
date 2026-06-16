from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8321/v1", api_key="fake")

response = client.responses.create(
    model="openai/gpt-4o-mini",
    input="Hi?",
)
print(response.output_text)
