https://github.com/HKUDS/nanobot

>> Setup uv environment
$ source .venv/bin/activate >>> to start nanobot environment
$ uv tool install nanobot-ai  >>> "tool install" option allows running nanobot without using "uv run"

>> Configuration check/set
$ nanobot status
$ nanobot onboard --wizard --config "/root/.nanobot/config.json"

$ nanobot agent
  /model OpenAI >> to switch model

$ nanobot webui -c "/root/.nanobot/config.json"


$ nanobot webui >>> do not enable websocket in WSL
$ cat ~/.nanobot/config.json | grep websocket
$ nanobot webui >>> access via webui
$ nanobot webui --background 

>> To access/work with the agent directly:
$ nanobot agent -w /home/yeokh/wrk -m "what model am I working with now"

>> TUI
$ uv run nanobot agent -w /home/yeokh/wrk
