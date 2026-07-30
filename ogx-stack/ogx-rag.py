import os
from openai import OpenAI

ogx_host = os.environ.get("OGX_HOST", "http://127.0.0.1:8321")
client = OpenAI(base_url=f"{ogx_host}/v1", api_key="fake")

MODEL = os.environ.get("OGX_MODEL", "openai/gpt-5-mini")

print("Ingest README.md into vector store and ask question via chat completions")

with open("README.md", "r") as f:
    doc_content = f.read()

# Upload a document
file = client.files.create(
    file=open("README.md", "rb"),
    purpose="assistants",
)

# Create a vector store and index the file
vector_store = client.vector_stores.create(
    name="readme",
    file_ids=[file.id],
)

print(f"Vector store created: {vector_store.id}")

system_prompt = f"""You are a helpful assistant. Use the following document to answer the user's question.

<document>
{doc_content}
</document>"""

question = "How to start ogx?"

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ],
)
print(response.choices[0].message.content)
