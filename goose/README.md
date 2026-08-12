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

ACP HTTP+SSE Server (acp-server.py) + Client (acp-client.py)
=============================================================
Splits acp-chat.py into two independent programs that communicate over HTTP
instead of stdio. The server bridges a `goose acp` subprocess to HTTP+SSE;
the client connects from anywhere on the network, including remote machines.

Install (one-time):
$ pip3 install flask werkzeug requests

acp-server.py — Goose ACP HTTP+SSE bridge
------------------------------------------
Spawns `goose acp` as a subprocess and exposes it over HTTP. Each session
gets a private temporary "transfer area" directory for file exchange; it is
deleted automatically when the server exits.

Endpoints:
  GET  /health                   liveness check → {"status": "ok"|"down"}
  GET  /info                     provider, model, goose command
  GET  /events                   SSE stream: notifications, permission requests,
                                 and file_created events for new agent output files
  POST /rpc                      forward a JSON-RPC request; blocks until goose responds
  POST /reply                    forward a client reply to a permission request
  POST /notify                   fire-and-forget notification to goose
  POST /files/<session_id>       upload a file into the session transfer area
  GET  /files/<session_id>       list files in the session transfer area
  GET  /files/<session_id>/<fn>  download a file from the session transfer area

Usage:
$ python3 acp-server.py                   # listens on http://127.0.0.1:7464
$ python3 acp-server.py --port 7464
$ python3 acp-server.py --builtin developer,memory
$ python3 acp-server.py --host 0.0.0.0   # allow remote clients
$ python3 acp-server.py --help

acp-client.py — Standalone chat client
---------------------------------------
Interactive terminal chat client that connects to acp-server.py over HTTP.
Streaming responses and permission prompts arrive via SSE. Includes file I/O
commands for uploading local files to the agent and downloading its outputs.

Usage:
$ python3 acp-client.py                               # connects to http://127.0.0.1:7464
$ python3 acp-client.py --server http://localhost:7464
$ python3 acp-client.py --server http://remote-host:7464 --cwd /my/project
$ python3 acp-client.py --downloads ./output          # where auto-downloads are saved
$ python3 acp-client.py --help

Chat commands:
  /quit                        Exit the chat
  /session                     Show session ID and transfer area path
  /cancel                      Cancel an in-progress agent response
  /ls [dir]                    List local directory (default: .)
  /attach <file> [message]     Upload a local file to the server transfer area;
                               auto-sends a prompt telling the agent its path
  /rls                         List files in the server transfer area
  /download <name> [local]     Download a file from the server transfer area
  /save [file]                 Save the last agent response text to a local file

File transfer model:
  Each session has a private temp directory on the server (the "transfer area").
  /attach uploads a file there and tells the agent the full server-side path so
  it can read it. When the agent writes new files to that path, a file_created
  SSE event is emitted and the client automatically downloads them to the
  --downloads directory (default: current directory). The transfer area is
  deleted when the server exits — only files saved by the client persist.

Typical workflow:
  You: /attach report.csv Analyse this CSV and write a summary.
    → uploads report.csv to /tmp/acp-abc123/report.csv
    → sends: "File 'report.csv' has been placed at /tmp/acp-abc123/report.csv.
              Analyse this CSV and write a summary."
  Goose: [reads the CSV, writes summary.md to /tmp/acp-abc123/]
    → SSE file_created: summary.md
    → [file] summary.md (2.1 KB) — downloading…
    → [file] saved → ./summary.md

Running locally (two terminals):
$ python3 acp-server.py                              # Terminal 1
$ python3 acp-client.py                              # Terminal 2

Running with a remote client:
$ python3 acp-server.py --host 0.0.0.0              # server machine
$ python3 acp-client.py --server http://<ip>:7464   # client machine

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
  requirements.txt      Python dependencies (flask, werkzeug, requests)
