https://github.com/ogx-ai/ogx
https://ogx-ai.github.io/docs/getting_started/quickstart

$ cd ogx-stack
$ uv init
$ uv sync
$ uv add 'ogx[starter]' openai

$ export ANTHROPIC_API_KEY="sk-ant-api03-xxx"

$ export OPENROUTER_API_KEY="sk-or-v1-xxx"
$ export OPENAI_API_KEY="$OPENROUTER_API_KEY"
$ export OPENAI_BASE_URL="https://openrouter.ai/api/v1"

$ uv run ogx run starter

>> On a separate terminal, we can start to use OGX API server/services... 

$ curl -s http://127.0.0.1:8321/v1/models 
$ curl -s http://127.0.0.1:8321/v1/models | jq -r '.data[].id'
$ curl -s http://127.0.0.1:8321/v1/providers | jq
$ curl -s http://127.0.0.1:8321/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer fake" \
  -d '{
    "model": "openai/gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Hello from curl"}
    ]
  }'



$ uv run ogx-list.py
$ uv run ogx-chat.py
$ uv run ogx-rag.py

$ podman run -it --rm -p 8321:8321 \
    -e OPENAI_API_KEY="sk-or-v1-xxx" \
    -e OPENAI_BASE_URL="https://openrouter.ai/api/v1" \
    ogxai/distribution-starter

$ podman run --entrypoint /bin/bash ...
# /usr/local/bin/ogx-entrypoint.sh

  
