Anthropic Managed Agents

https://platform.claude.com/docs/en/managed-agents/quickstart#curl-(linux/wsl)


# mkdir ant; cd ant

# VERSION=1.10.0
# OS=$(uname -s | tr '[:upper:]' '[:lower:]')
# ARCH=$(uname -m | sed -e 's/x86_64/amd64/' -e 's/aarch64/arm64/')
# curl -fsSL "https://github.com/anthropics/anthropic-cli/releases/download/v${VERSION}/ant_${VERSION}_${OS}_${ARCH}.tar.gz" | sudo tar -xz -C /usr/local/bin ant

# ant --version

uv init
uv sync
source .venv/bin/activate
uv add anthropic

ant beta:agents create   --name "Coding Assistant"   --model '{id: claude-opus-4-8}'   --system "You are a helpful coding assistant. Write clean, well-documented code."   --tool '{type: agent_toolset_20260401}'

>> https://platform.claude.com/docs/en/build-with-claude/working-with-messages

# ant messages create \
  --model claude-haiku-4-5 \
  --max-tokens 1024 \
  --message '{role: user, content: "Hello, Claude"}'


