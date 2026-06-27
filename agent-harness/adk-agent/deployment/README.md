podman build -t quay.io/khyeo/adk-agent-web:v1 -f Containerfile.web .
podman login ...>> make sure the login has the authority to write to the repo
podman push ... >> Go to the repo settings to allow the user/robot account has access

Test with Podman:

**1. Create the volumes:**
podman volume create adk-agent-agent
podman volume create adk-agent-input
podman volume create adk-agent-output

**2. export OPENROUTER_API_KEY="sk-or-v1-xxx..."

**3. Run the container:**
podman run --rm -it --name adk-agent \
  -p 8080:8080 \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e API_PROVIDER=anthropic \
  -e MODEL=claude-haiku-4-5  \
  -v adk-agent-agent:/app/agent \
  -v adk-agent-input:/app/input \
  -v adk-agent-output:/app/output \
  quay.io/khyeo/adk-agent-web:v1

Then open http://localhost:8080 in your browser.



