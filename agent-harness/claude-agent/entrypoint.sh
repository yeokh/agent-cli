#!/bin/sh
# RUN_MODE=web  -> Flask web UI on port 8080
# RUN_MODE=agent (default) -> headless batch run
if [ "$RUN_MODE" = "web" ]; then
    exec python /app/web_app.py
else
    exec python /app/claude_agent.py
fi
