https://github.com/lightspeed-core/lightspeed-stack/blob/main/README.md
https://github.com/openshift/lightspeed-agentic-operator
https://github.com/lightspeed-core/lightspeed-reference-ui
https://github.com/lightspeed-core/llama-stack-runner/tree/main

0. download repo
git clone https://github.com/lightspeed-core/lightspeed-stack.git
cd lightspeed-stack
git submodule update --init

1. install dependencies using uv
uv sync --group dev --group llslibdev

2. create llama stack run.yaml. you can do this by running the local run generation script
./scripts/generate_local_run.sh

3. export the LLM token environment variable that Llama stack requires. 
export OPENROUTER_API_KEY=sk-xxxxx
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
export OPENAI_API_KEY="$OPENROUTER_API_KEY"
export OPENAI_MODEL="openai/anthropic/claude-haiku-4.5"

4. start LCS server - 
make run

5. access LCS web UI at http://localhost:8080/
