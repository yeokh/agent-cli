tandy - Mock API Service for Tandem
===================================
A complete FastAPI implementation that mimics the payload schema and response structure of Tandem api. 
It forwards the incoming parameters to OpenAI's official v1/chat/completions API (using openai>=1.0.0) while excluding authentication, guardrails, embeddings, content filtering, and RAG functionality.

$ uv add fastapi uvicorn openai pydantic
$ export OPENAI_API_KEY="sk-proj-your-actual-key"
$ python app.py

$ curl -X POST "http://localhost:8000/TandemApi"   -H "Content-Type: application/json"    -d '{
    "userId": "test@synapxe.sg", "message": "User: My name is John. Greet me in one sentence.\nAssistant: Hello, John-nice to meet
 you!\nUser: What is my name?", "chat_model": "gpt-5-mini", "streaming": "false" }' | jq

Output >>>
{
  "results": {
    "chat_model": "gpt-5-mini",
    "chat_tokens": 255,
    "injected_chatprompt": null,
    "message": "User: My name is John. Greet me in one sentence.\nAssistant: Hello, John-nice to meet you!\nUser: What is my name?",
    "message_id": "f23fb3bc-d4c0-4485-a166-9870a979fb9b",
    "response": "Your name is John.",
    "session_id": null,
    "user_id": "test@synapxe.sg"
  }


curl -X POST "http://localhost:8000/TandemApi" \
  -H "Content-Type: application/json" \
 -d '{
    "userId": "test@synapxe.sg",
    "message": "Give me a 1-sentence health tip.",
    "chat_model": "gpt-5-mini",
    "streaming": "false"
  }' | jq

>> Output
{
  "results": {
    "chat_model": "gpt-5-mini",
    "chat_tokens": 124,
    "injected_chatprompt": null,
    "message": "Give me a 1-sentence health tip.",
    "message_id": "36e9a82d-0992-47f4-a609-dd1430e5ec81",
    "response": "Aim for 7–9 hours of quality sleep each night to boost mood, memory, immunity, and overall health.",
    "session_id": null,
    "user_id": "test@synapxe.sg"
  }
}

