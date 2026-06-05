https://adk.dev/get-started/python/

Google Agent Development Kit (ADK)

# uv init adk; cd adk
# uv sync
# source .venv/bin/activate

# uv pip install google-adk
# uv pip install google-adk[extensions]

# adk create ant_agent   >> Folder name cannot have dash
# ls ant_agent; vi ./ant_agent/agent.py 

Note: Expected adk agent directory structure:
  <agents_dir>/
    my_agent/
      agent.py (with root_agent) OR
      root_agent.yaml

# adk run ant_agent
# adk web ant_agent

ant_agent >> Anthropic
or_agent >> OpenRouter, Ollama or equivalent
