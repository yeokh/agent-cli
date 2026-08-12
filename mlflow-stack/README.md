https://mlflow.org/docs/latest/genai/governance/ai-gateway/quickstart/

uv init
uv sync
source .venv/bin/activate

uv pip install 'mlflow[genai]'
mlflow server --port 5000
