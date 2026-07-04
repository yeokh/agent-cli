#!/usr/bin/env bash
set -euo pipefail

SHARED_PROJECT="project00"

echo "Creating shared project: $SHARED_PROJECT..."
oc create namespace "$SHARED_PROJECT"

# 1. Allow all authenticated users to VIEW resources in project00
oc adm policy add-role-to-group view system:authenticated -n "$SHARED_PROJECT"

# 2. Apply NetworkPolicy to allow cross-namespace ingress traffic from user projects
cat <<EOF | oc apply -n "$SHARED_PROJECT" -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-all-user-projects
spec:
  podSelector: {}
  ingress:
  - from:
    - namespaceSelector: {}
  policyTypes:
  - Ingress
EOF

echo "Shared project $SHARED_PROJECT created with global read-only and network access."

