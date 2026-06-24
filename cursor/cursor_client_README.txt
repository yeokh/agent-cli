There are a few ways to use Cursor:
- GUI/TUI interactive agent/client
- Cursor Agent Communication Protocol (ACP) service - see acp_client.py
- Curlor SDK - see cursor_client.py

Date: June 2026

The error is not from your API key or AgentOptions setup — it's a bug in cursor-sdk 0.1.7 when launching the local
  bridge.

  Root cause

  When you call Agent.create() with local=..., the SDK starts a cursor-sdk-bridge subprocess and passes callback
  auth tokens as CLI arguments:

  --tool-callback-auth-token <token>

  Those tokens are generated with secrets.token_urlsafe(32), which can start with - (about 1–2% of the time). The
  bridge's argument parser treats any value starting with - as a new flag, so it throws:

  Missing value for --tool-callback-auth-token

  That's why the failure looks random — it depends on the generated token.

  Fix applied

  I added a small workaround at the top of cursor_client.py that patches token generation to skip values starting
  with -. Verified with 50 consecutive bridge launches — all succeeded.

  I also made two related fixes you'd hit next:

  1. model="composer-2.5" — current SDK model id (replacing "composer")
  2. run.text() — agent.send() returns a Run object, not the response string

  Run it again with your API key set:

  export CURSOR_API_KEY="crsr_xxx"
  uv run cursor_client.py

  This workaround is specific to cursor-sdk 0.1.7. Once Cursor ships a fix (e.g. using
  --tool-callback-auth-token=<value> or quoting), you can remove the patch block at the top of the file.
