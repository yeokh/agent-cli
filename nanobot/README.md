https://github.com/HKUDS/nanobot

$ source .venv/bin/activate >>> to start nanobot environment
$ nanobot webui >>> do not enable websocket in WSL
$ cat ~/.nanobot/config.json | grep websocket
$ nanobot webui >>> access via webui
$ nanobot webui --background 

>> To access/work with the agent directly:
$ nanobot agent -w /home/yeokh/wrk -m "what model am I working with now"

>> TUI
$ uv run nanobot agent -w /home/yeokh/wrk
