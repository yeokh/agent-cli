from openai import OpenAI

client = OpenAI(base_url="http://localhost:8321/v1", api_key="fake")

# First turn
qry = "Hi, my name is Alice"
print("Me:", qry)

r1 = client.responses.create(
    model="anthropic/claude-haiku-4-5-20251001",
    input=qry,
)
print("Assistant:", r1.output_text)

# Second turn - references the first
qry = "What did I say may name was?"
print("Me:", qry)

r2 = client.responses.create(
    model="anthropic/claude-haiku-4-5",
    input=qry,
    previous_response_id=r1.id,
)
print("Assistant:", r2.output_text)
