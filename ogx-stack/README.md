https://github.com/ogx-ai/ogx
https://ogx-ai.github.io/docs/getting_started/quickstart

$ cd ogx-stack
$ uv init
$ uv sync
$ uv add 'ogx[starter]' openai

$ export ANTHROPIC_API_KEY="sk-ant-api03-xxx"

$ export OPENROUTER_API_KEY="sk-or-v1-xxx"
$ export OPENAI_API_KEY="$OPENROUTER_API_KEY"
$ export OPENAI_BASE_URL="https://openrouter.ai/api/v1"

$ uv run ogx run starter

>> On a separate terminal, we can start to use OGX API server/services... 

$ curl -s http://127.0.0.1:8321/v1/models 
$ curl -s http://127.0.0.1:8321/v1/models | jq -r '.data[].id'
$ curl -s http://127.0.0.1:8321/v1/providers | jq
$ curl -s http://127.0.0.1:8321/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer fake" \
  -d '{
    "model": "openai/gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Hello from curl"}
    ]
  }'



$ uv run ogx-list.py
$ uv run ogx-chat.py
$ uv run ogx-rag.py

$ podman run -it --rm -p 8321:8321 \
    -e OPENAI_API_KEY="sk-or-v1-xxx" \
    -e OPENAI_BASE_URL="https://openrouter.ai/api/v1" \
    ogxai/distribution-starter

$ podman run --entrypoint /bin/bash ...
# /usr/local/bin/ogx-entrypoint.sh


OpenShift Deployment - OGX Starter
==================================
$ vi deploy-ogx.yaml
$ oc login ...
$ oc project <my_project>
$ oc apply -f deploy-ogx.yaml
$ oc get services >> internal fqdn end-point (only from within OpenShift) 
$ oc get routes   >> external fqdn end-point

$ curl -s https://distribution-starter-route-aa-ogx-stack.apps.ocp.b7785.sandbox5220.opentlc.com/v1/chat/completions \
  -H "Content-Type: application/json"   -H "Authorization: Bearer fake" \
  -d '{
    "model": "openai/openai/gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Hello. Response in one word.  What is the capital of India."}
    ]
  }'


The list of available providers/models can be provided via dynamic passthrough to the providers or via a defined list of models.

Dynamic Way (Passthrough)
The client applications can access the models directly available on providers.  
OGX proxy will forward whatever model string your client requests directly to the providers. 

Pre-defined List (Enforced List via ConfigMap)
To restrict a curated list of providers/models, or to map to custom aliases, we need to use a configuration file (run.yaml).  
We can set this up using OpenShift ConfigMap.


References:
RAG with OGX - https://developers.redhat.com/articles/2026/05/26/build-enterprise-rag-system-ogx#  
Upstream OGX deployment on k8s - https://ogx-ai.github.io/docs/deploying/kubernetes_deployment
OGX OpenShift deployment - https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/working_with_ogx/activating-the-ogx-operator_rag


Simple OGX with API Token (TO TEST)
=========================
Out of the box, no. The ogxai/distribution-starter (OGX/Llama Stack architecture) is designed to act as an open applicat
ion gateway middleware. It does not feature a native inbound API_KEY configuration flag to secure its own endpoints (whi
ch is why the official documentation examples tell you to pass api_key="fake" in your client SDK setup).

However, because you are deploying to OpenShift, yes, you can easily enforce this. The standard, production-grade way to
 secure an open middleware container is to offload authentication to a Sidecar Proxy Guard inside the same Pod.

By injecting a tiny Nginx container into your deployment, you can intercept incoming traffic, validate a custom Authoriz
ation: Bearer <token> header against an OpenShift Secret, and only pass authorized traffic through to OGX.

<deploy-ogx-nginx.yaml>

OpenShift Route and Service point directly to port 8322 (the Nginx proxy), while OGX listen on port 8321.

When an external client calls your application, Nginx inspects the incoming $http_authorization header.

If the token matches your INBOUND_ACCESS_TOKEN secret exactly, Nginx forwards the payload over the local loopback interface (127.0.0.1:8321) into the OGX container. If it doesn't match, it drops the connection instantly with a 401 Unauthorized response.

Now when you initialize your OpenAI client or make curl requests, you replace "fake" with your specific inbound secret.


