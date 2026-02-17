# SoziCheckSG (FastAPI Scaffold)

Step 2 scaffold for a production-style rewrite using:
- FastAPI backend
- Jinja2 templates
- TailwindCSS CDN
- Fetch-based frontend state machine
- Minimal vanilla JS

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Step 2 scope

- Single-button UX state machine implemented (`init` → `recording` → `ready`)
- `/initialize` transitions app into recording-ready state
- Typed input acts as temporary stand-in for audio in `recording` and `ready` states
- `/upload-audio` currently accepts JSON payload `{ "text": "..." }` and returns stub `{ "reply": "..." }`
- Chat bubbles auto-scroll and stay mobile-friendly
- Microphone recording intentionally **not implemented** yet
