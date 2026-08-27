# A2A Client for Hermes Gateway

Python clients for interacting with the Hermes A2A (Agent-to-Agent) gateway via JSONRPC over HTTP.

## Overview

This client provides a clean Python interface to communicate with the Hermes Agent gateway running on `127.0.0.1:9900`.

**Gateway Status:** ✓ Running and verified  
**Agent:** `hermes-rhel9wsl` v1.0.0  
**Available Skills:** 33 toolsets  
**Protocol:** JSONRPC 1.0  

## Files

- `a2a_client.py` — A2A client library + integration test suite
- `a2a_chat.py` — Interactive streaming chat client (modelled after `goose/acp-client.py`)
- `README_A2A.md` — This file

## Requirements

- Python 3.7+
- `requests` library

```bash
pip install requests
```

---

## a2a_chat.py — Interactive Chat Client

An interactive terminal chat client that connects to the Hermes A2A gateway using the
`message/stream` endpoint for live SSE streaming output, with multi-turn conversation
support via `contextId`.

### Quick Start

```bash
python3 a2a_chat.py
python3 a2a_chat.py --server http://localhost:9900
```

### Chat Commands

| Command | Description |
|---|---|
| `/quit` | Exit the client |
| `/session` | Show the current `contextId` |
| `/new` | Start a fresh conversation (new context) |
| `/skills` | List all available toolsets |

### Protocol

| | ACP (Goose `acp-client.py`) | A2A (Hermes `a2a_chat.py`) |
|---|---|---|
| Transport | `POST /rpc` + SSE on `GET /events` | Single `POST /` with SSE response |
| Method | `session/prompt` | `message/stream` |
| SSE model | Background thread queues events | Direct `iter_lines` on streaming response |
| Continuity | `sessionId` | `contextId` |

SSE frames emitted by `message/stream`:

```
data: {"result": {"task": {"id": "...", "contextId": "..."}}}
data: {"result": {"statusUpdate": {"status": {"state": "TASK_STATE_WORKING"}}}}
data: {"result": {"artifactUpdate": {"artifact": {"parts": [{"text": "..."}]}}}}
data: {"result": {"statusUpdate": {"status": {"state": "TASK_STATE_COMPLETED"}}}}
: done
```

### API Usage

```python
from a2a_chat import HermesA2AClient

client = HermesA2AClient("http://127.0.0.1:9900")

# Single turn
result = client.send_stream("What is 2+2?", on_chunk=print)
context_id = result["context_id"]

# Continue the conversation
result = client.send_stream("And 3+3?", context_id=context_id, on_chunk=print)

client.close()
```

---

## a2a_client.py — Test Suite & Library

### Quick Start

```bash
python3 a2a_client.py
```

### API Usage

```python
from a2a_client import A2AClient

client = A2AClient()

if client.is_healthy():
    print("Gateway is running")

response = client.get_agent_card()
if response.success:
    agent_name = response.data['name']

response = client.call_jsonrpc("method_name", {"param": "value"})
```

### Test Results

All critical tests passed:

✓ Gateway Accessibility  
✓ Agent Card Retrieval  
✓ JSONRPC Interface Check  
✓ Gateway Capabilities (streaming, push notifications)  
✓ 33 Skills/Toolsets Available  

---

## Gateway Capabilities

- **Streaming:** ✓ Enabled
- **Push Notifications:** ✓ Enabled
- **State Transition History:** ✗ Not available
- **Extended Agent Card:** ✗ Not available

## Available Toolsets

| Toolset | Operations |
|---|---|
| a2a | 6 |
| bfl | 7 |
| browser | 11 |
| browser-cdp | 3 |
| browser-use | 2 |
| clarify | 2 |
| code_execution | 2 |
| computer_use | 2 |
| cronjob | 2 |
| delegation | 2 |
| desktop_ui | 10 |
| discord | 2 |
| discord_admin | 2 |
| feishu_doc | 1 |
| feishu_drive | 4 |
| file | 5 |
| hermes-yuanbao | 4 |
| homeassistant | 4 |
| image_gen | 2 |
| kanban | 12 |
| memory | 2 |
| project | 3 |
| session_search | 2 |
| skills | 3 |
| spotify | 6 |
| terminal | 2 |
| todo | 2 |
| tts | 2 |
| video | 2 |
| video_gen | 3 |
| vision | 2 |
| web | 3 |
| x_search | 2 |
