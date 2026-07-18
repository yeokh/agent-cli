Community Goose
=============== 
https://github.com/aaif-goose/goose

Goose CLI:
$ sudo dnf install bzip2  # Pre-req to install
$ curl -fsSL https://github.com/aaif-goose/goose/releases/download/stable/download_cli.sh | bash

$ goose configure
$ cat /root/.config/goose/config.yaml

$ goose  
$ goose session list
$ goose session -n 20260628_3 --resume

https://goose-docs.ai/docs/tutorials/goose-in-docker

.goosehints - project/folder level instructions file.




RED HAT Version of Goose
========================
Goose with RHEL - https://interact.redhat.com/share/Z42Lt4N7qGKWKSNhmHhk

https://access.redhat.com/articles/7142302

Use instructions to run agent jobs with Goose:
goose run -i <path to instruction> -s

ACP Chat (acp-chat.py)
======================
Interactive terminal chat client for the Goose ACP (Agent Client Protocol) server.
Communicates with a `goose acp` subprocess over JSON-RPC 2.0 via stdio.

Features:
- Real-time streaming of agent responses as they arrive
- Live tool-call status display (pending / completed / error)
- Interactive permission prompts for sensitive tool operations
- Session management (create, cancel, inspect)

Usage:
$ python3 acp-chat.py                            # default: --builtin developer
$ python3 acp-chat.py --builtin developer,memory
$ python3 acp-chat.py --cwd /my/project
$ python3 acp-chat.py --help

Chat commands:
  /quit     Exit the chat
  /session  Print the current session ID
  /cancel   Cancel an in-progress agent response

ACP Protocol reference:
https://block-goose.mintlify.app/advanced/acp-protocol

ACP Web UI (acp-web.py)
=======================
Flask-based web interface for the Goose ACP server.
Spawns a `goose acp` subprocess and exposes a browser UI at http://localhost:8082.

Features:
- Sidebar file browser: navigate folders, upload (drag-and-drop or browse),
  download, delete files, and create folders within the working directory
- Working folder selector: type any path and click Set to restart the session
  in a new directory (created automatically if it does not exist)
- Chat panel: streaming agent responses, inline tool-call status cards,
  and interactive permission-request cards with allow/reject buttons
- Status indicator: live provider, model, and session info with a colour-coded dot
- Reconnect button: restart the goose session without reloading the page

Default working directory: ./workspace  (created next to acp-web.py on first run)

Usage:
$ pip3 install flask werkzeug          # one-time install
$ python3 acp-web.py                   # http://localhost:8082
$ python3 acp-web.py --port 8083
$ python3 acp-web.py --cwd /my/project
$ python3 acp-web.py --builtin developer,memory
$ python3 acp-web.py --help

Files:
  acp-web.py            Flask backend (ACP client + REST + SSE endpoints)
  templates/index.html  Single-page web UI (HTML/CSS/JS, no build step)
  requirements.txt      Python dependencies (flask, werkzeug)
