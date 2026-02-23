# pharma-agent-ai

## Run the app (single server)

From repo root:

```bash
cd backend/app
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Then open:

- http://127.0.0.1:8000

The frontend is served by FastAPI, so you do not need a separate frontend server.

## Run without typing commands each time

### macOS

Double-click:

- `start_pharma_app.command`

This script starts the backend (if not already running) and opens the app in your browser.

### Windows

Double-click:

- `start_pharma_app.bat`

This script starts the backend in a new Command Prompt window (if not already running) and opens the app in your browser.
