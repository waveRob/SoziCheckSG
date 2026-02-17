# SoziCheckSG (FastAPI Scaffold)

Step 1 scaffold for a production-style rewrite using:
- FastAPI backend
- Jinja2 templates
- TailwindCSS CDN
- HTMX
- Minimal vanilla JS state machine

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Step 1 scope

- Project structure scaffolded under `app/`
- Required endpoints added with placeholder behavior
- Single-button UI state machine scaffolded
- Microphone recording intentionally **not implemented** yet
