#!/usr/bin/env bash
set -euo pipefail

NUM_USERS=20
MANIFEST_PATH="./user-resources.yaml" # Path to your k8s/oc manifest file

if [ ! -f "$MANIFEST_PATH" ]; then
    echo "Error: Manifest file not found at $MANIFEST_PATH"
    exit 1
fi

# Apply the manifest template to each user's project namespace
for i in $(seq -w 1 "$NUM_USERS"); do
    PROJECT_NAME="user${i}-project"
    echo "Deploying resources to $PROJECT_NAME..."
    
    oc apply -f "$MANIFEST_PATH" -n "$PROJECT_NAME"
done

echo "Resources successfully pre-deployed across all 20 user projects."
