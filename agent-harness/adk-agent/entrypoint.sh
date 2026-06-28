#!/bin/sh
# RUN_MODE=web  -> Flask web UI (default: agent)
# RUN_MODE=agent -> headless batch run
if [ "$RUN_MODE" = "web" ]; then
    exec python /app/web_app.py
else
    exec python /app/adk_agent.py
fi
