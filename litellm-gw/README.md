LiteLLM Experimental Projects

If you are running LiteLLM in an air-gapped, offline, or firewalled environment (like Docker containers or corporate networks), set these environment variables to skip all network timeouts completely:

Bash
# Skip fetching the cost map from GitHub and immediately use the local backup file
export LITELLM_LOCAL_MODEL_COST_MAP=True

# Disable remote telemetry and version checking calls
export LITELLM_TELEMETRY=False
export DISABLE_LITELLM_VERSION_CHECK=True

# Tell tiktoken to read BPE files from a pre-downloaded local folder instead of fetching over web
export TIKTOKEN_CACHE_DIR="/path/to/pre_downloaded_tiktoken_cache"


custom-provider - Example liteLLM gateway for a custom back-end.

tandy - Mock API Service for T.
Below is a complete FastAPI implementation that mimics the payload schema and response structure of T api. It forwards the incoming parameters to OpenAI's official v1/chat/completions API (using openai>=1.0.0) while excluding authentication, guardrails, embeddings, content filtering, and RAG functionality.

pip install fastapi uvicorn openai pydantic
export OPENAI_API_KEY="sk-proj-your-actual-key"
python tandy.py

curl -X POST "http://localhost:8000/TandemApi" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "test@synapxe.sg",
    "message": "Give me a 1-sentence health tip.",
    "chat_model": "gpt4o",
    "streaming": "false"
  }'


