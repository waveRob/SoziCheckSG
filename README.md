# SoziCheckSG (FastAPI App)

FastAPI rewrite of the Sozialhilfe check assistant with:
- browser microphone recording
- speech-to-text transcription
- editable transcription review
- OpenAI chat response generation
- Google Cloud text-to-speech playback
- multilingual startup + conversation prompt based on `prompts.yaml`

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Environment

The app expects these variables (already used in your Gradio flow):
- `OPENAI_API_KEY`
- `GOOGLE_CREDENTIALS` (JSON service account payload)

## UX flow

1. **Initialize**: locks language, loads the social-check prompt, plays intro audio.
2. **Start Recording / Stop**: captures microphone and sends audio to backend transcription.
3. **Review & Edit**: user edits transcribed text.
4. **Send**: backend generates bot answer and returns audio playback.
