WSL host for AI agents and agentic AI experiments
- https://openkaiden.ai/
- https://github.com/NVIDIA/OpenShell
- https://www.redhat.com/en/blog/bringing-claude-self-hosted-sandboxes-to-openshell-on-red-hat-ai
- https://www.redhat.com/en/blog/red-hat-ai-and-openshell-driving-security-enhanced-agent-execution-for-enterprise-ai

Sandboxing AI agents in isolated execution/runtime environment in micro-VM, container etc.
Take note that some AI agents can also run tasks/tools/sub-agents in isolated environment.


==============
Confirgure WSL
==============
vi /etc/wsl.conf
[boot]
systemd = false

[network]
hostname = rhel9wsl

[interop]
appendWindowsPath = false


============
Installation
============

https://console.redhat.com/openshift/downloads
https://odo.dev/docs/overview/installation/
- helm, oc, kubectl and odo
https://odo.dev/docs/user-guides/quickstart/go

# subscription-manager register
Registering to: subscription.rhsm.redhat.com:443/subscription
Username: keyeo@redhat.com

The system has been registered with ID: 39ae45a6-07d6-4035-9839-93b4ae0311f4
The registered system name is: rhel9wsl
# dnf update -y
# dnf install -y rhc

# dnf install -y command-line-assistant rhc >> Not working. Does not support WSL.
# dnf remove -y command-line-assistant rhc

Install:
- mc, nano
- uv -V, uv self update
- python3 --version
- podman version

######
Cursor
######

https://cursor.com/docs/cli/overview
curl https://cursor.com/install -fsS | bash
agent -v, agent update, agent login, agent about, agent --trust -p "hi"

#####
Codex
#####

https://openrouter.ai/docs/cookbook/coding-agents/codex-cli
https://github.com/openai/codex

# sudo npm install -g @openai/codex    >> use sudo to ensure it install in wsl
# whereis codex && which codex
/usr/local/bin/codex

# mkdir ~/.codex && vi ~/.codex/config.toml
model_provider = "openrouter"
model_reasoning_effort = "high"
model="openai/gpt-5.3-codex"
[model_providers.openrouter]
name = "openrouter"
base_url="https://openrouter.ai/api/v1"
env_key="OPENROUTER_API_KEY"

# export OPENROUTER_API_KEY="sk-or-..."

# cd /path/to/your/project
# codex 

======
Claude
======
https://code.claude.com/docs/en/quickstart
curl -fsSL https://claude.ai/install.sh | bash

# which claude
# claude --version, claude doctor, claude update

====== 
pi.dev
======
https://pi.dev/
https://github.com/earendil-works/pi
curl -fsSL https://pi.dev/install.sh | sh

# export ANTHROPIC_API_KEY=sk-ant-...
# pi
/login


======
Gemini
======
https://docs.google.com/document/d/1-c4QBDuT9STwqU-Txb7C86VgHggeD8p4Lum1gnNHSxI/
https://geminicli.com/docs/get-started/installation/

# export GOOGLE_CLOUD_PROJECT="agentspace-301617"
# echo 'export GOOGLE_CLOUD_PROJECT="agentspace-301617"' >> ~/.bashrc
# source ~/.bashrc

# gemini
/about


========
opencode
========

https://opencode.ai/docs/cli/
https://github.com/anomalyco/opencode

curl -fsSL https://opencode.ai/install | bash

# opencode
export PATH=/root/.opencode/bin:$PATH


