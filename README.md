# SoziCheckSG (FastAPI Scaffold)

Step 2 scaffold for a production-style rewrite using:
- FastAPI backend
- Jinja2 templates
- TailwindCSS CDN
- Fetch-based frontend state updates

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Step 2 scope

- Single-button state machine implemented (`init` -> `recording` -> `ready`)
- Temporary typed text input used as a stand-in for microphone capture
- `POST /upload-audio` currently accepts JSON payload `{ "text": "..." }`
- No microphone recording code implemented yet
