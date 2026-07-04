#!/usr/bin/env bash
set -euo pipefail

NUM_USERS=20
PASSWORD="r3dh4t"
HTPASSWD_FILE="workshop.htpasswd"
SECRET_NAME="workshop-htpasswd-secret"

echo "Creating local htpasswd file..."
rm -f "$HTPASSWD_FILE"

# 1. Generate htpasswd entries
for i in $(seq -w 1 "$NUM_USERS"); do
    USERNAME="user$i"
    if [ ! -f "$HTPASSWD_FILE" ]; then
        htpasswd -B -c "$HTPASSWD_FILE" "$USERNAME" "$PASSWORD"
    else
        htpasswd -B "$HTPASSWD_FILE" "$USERNAME" "$PASSWORD"
    fi
done

# 2. Upload htpasswd to OpenShift Config Namespace
oc create secret generic "$SECRET_NAME" \
    --from-file=htpasswd="$HTPASSWD_FILE" \
    --dry-run=client -o yaml | oc apply -n openshift-config -f -

# 3. Apply OAuth Configuration to Cluster
cat <<EOF | oc apply -f -
apiVersion: config.openshift.io/v1
kind: OAuth
metadata:
  name: cluster
spec:
  identityProviders:
  - name: workshop-htpasswd-idp
    mappingMethod: claim
    type: HTPasswd
    htpasswd:
      fileData:
        name: $SECRET_NAME
EOF

# 4. Provision isolated user projects and assign RBAC
for i in $(seq -w 1 "$NUM_USERS"); do
    USERNAME="user$i"
    PROJECT_NAME="${USERNAME}-project"
    
    echo "Provisioning $PROJECT_NAME..."
    oc create namespace "$PROJECT_NAME"
    oc adm policy add-role-to-user admin "$USERNAME" -n "$PROJECT_NAME"
done

rm -f "$HTPASSWD_FILE"
echo "User accounts and default projects successfully created."
