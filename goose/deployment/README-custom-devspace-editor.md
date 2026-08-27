Create a Custom Dedicated ConfigMap to Add Custom Editor
========================================================
Instead of modifying the operator-managed ConfigMap, OpenShift Dev Spaces requires you to create a new, separate ConfigMap for custom editor definitions. The operator automatically scans the openshift-devspaces namespace for any ConfigMap carrying specific labels and merges them into the dashboard.

Step 1: Create a dedicated ConfigMap for the Web Terminal
Run the following command to create a standalone ConfigMap (e.g., custom-editor-web-terminal):

oc create configmap custom-editor-web-terminal \
  --from-file=che-web-terminal-latest.yaml \
  -n openshift-devspaces

Step 2: Apply the required labels
Add the two mandatory labels that instruct the Dev Spaces operator to index this ConfigMap as a valid editor definition:

oc label configmap custom-editor-web-terminal \
  app.kubernetes.io/part-of=che.eclipse.org \
  app.kubernetes.io/component=editor-definition \
  -n openshift-devspaces --overwrite

Step 3: Verification
Verify the new ConfigMap exists:

oc get configmap custom-editor-web-terminal -n openshift-devspaces

Check Dev Spaces Dashboard:
Refresh your OpenShift Dev Spaces dashboard. The new Web Terminal editor option will now appear alongside the standard JetBrains and VS Code options without being overwritten by the operator.
