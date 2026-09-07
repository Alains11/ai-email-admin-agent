# AI Email Admin Agent

An API and command-line assistant for managing email and calendar workflows.

## Project Layout

```text
app/
  main.py                    FastAPI application entry point
  api/
    routes/chat.py           Chat HTTP endpoint
    models/chat.py           Chat request and response models
  integrations/
    email/                   Gmail, Outlook, and Yahoo adapters
    calendar/                Google Calendar adapter
  services/
    email_agent.py           AI orchestration and tool graph
    conversation_memory.py   SQLite chat-memory service
  workers/
    inbox_monitor.py         Optional proactive inbox monitor
scripts/
  chat_cli.py                Interactive API client
  google_oauth.py            Google OAuth token bootstrap utility
tests/
  services/                  Service-level tests
```

## Run

```bash
uvicorn app.main:app --reload
python scripts/chat_cli.py
```

To create or refresh a Google OAuth token, run `python scripts/google_oauth.py` from the repository root.
