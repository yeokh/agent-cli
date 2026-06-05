https://docs.crewai.com/en/installation

mkdir crewai; cd crewai; uv init; uv sync; source .venv/bin/activate
uv tool install crewai-cli
uv tool list
uv tool install crewai-cli --upgrade

cd wrk  >> Create crewai projects in wrk folder

crewai create crew <your_project_name>
Review and amend the following:
agents.yaml - Define your AI agents and their roles
tasks.yaml - Set up agent tasks and workflows
.env - Store API keys and environment variables
main.py	- Project entry point and execution flow
crew.py	- Crew orchestration and coordination
tools/	- Directory for custom agent tools
knowledge/ - Directory for knowledge base

crewai install
uv add <packages>
crewai run

