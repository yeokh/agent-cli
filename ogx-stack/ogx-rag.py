from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8321/v1", api_key="fake")

print("Ingest README.md into vector store and ask question with file_search tool")

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

# Ask questions with file search
response = client.responses.create(
    model="openai/anthropic/claude-haiku-4.5",
    input="How to start ogx?",
    tools=[{
        "type": "file_search",
        "vector_store_ids": [vector_store.id],
    }],
)
print(response.output_text)
