#!/bin/bash

# Set GOOSE_DOCS_ROOT environment variable for Goose documentation
export GOOSE_DOCS_ROOT="/root/assistants/ansible-builder/knowledge-base/documentation"

# Navigate to the ansible-builder directory
cd /root/assistants/ansible-builder

# Display startup message
cat << EOF
Welcome to the Ansible Builder Assistant!

Capabilities:
- Advisor         /advice  Offers explanations and guidance on existing playbooks.
- Spec Generator  /spec    Crafts structured playbook specifications from requirements.
- Playbook Writer /build   Develops high-quality, production-ready playbooks.
- Reviewer        /review  Delivers thorough analysis and review of playbooks with a focus on security and performance.
EOF

# Placeholder for starting Goose (replace with actual start command)
echo "Start Goose and say hi or /skills to show the list of skills..."

goose

