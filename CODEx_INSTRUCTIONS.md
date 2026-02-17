You are a senior full-stack engineer.

We are building a production-ready web application for a chatbot that currently exists as a Gradio app.

We are rewriting it completely using:

- FastAPI (backend)
- Jinja2 templates
- TailwindCSS (mobile-first design)
- HTMX (dynamic updates without heavy JS)
- Minimal vanilla JavaScript (only for microphone recording via MediaRecorder API)

The goal is a clean, modern, mobile-friendly app that works on:
- Desktop
- Tablets
- Phones

This is NOT a demo tool. It must look like a real product.

------------------------------------------------------------
CORE REQUIREMENTS
------------------------------------------------------------
Recording must be triggered by a real browser click event
(because of getUserMedia security restrictions).

There must be ONE main button that changes behavior depending on state.

State A: "Initialize"
State B: "Ready to Record"
State C: "Recording"
State D: "Review & Edit"
(plus a temporary "Busy" sub-state while transcribing/sending)

Button logic:

- When in "Initialize":
    - Initialize conversation/session
    - Selected Language will be set and can not be changed anymore
    - Transition to "Ready to Record"

- When in "Ready to Record":
    - Start microphone recording (MediaRecorder)
    - Transition to "Recording"

- When in "Recording":
    - Stop recording (MediaRecorder)
    - Upload raw audio to backend for speech-to-text ONLY
    - Backend returns transcription text
    - Populate an editable textbox/textarea with the transcription
    - Transition to "Review & Edit"

- When in "Review & Edit":
    - User can edit the transcription in the textbox/textarea
    - On button tap: send the edited text to backend
    - Backend calls OpenAI API and returns assistant response
    - UI updates chat (user bubble + assistant bubble)
    - Clear textbox and transition back to "Ready to Record"

Recording must be triggered by a real browser click event
(because of getUserMedia security restrictions).

------------------------------------------------------------
BACKEND REQUIREMENTS
------------------------------------------------------------

Use FastAPI.

Endpoints needed:

- GET /
    -> Main page

- POST /initialize
    -> Start scenario
    -> Store session state

- POST /upload-audio
    -> Accept recorded audio file
    -> Convert speech to text
    -> Call OpenAI
    -> Return assistant response (JSON)

- POST /generate-pdf
    -> Export conversation summary

Use session-based state (not global variables).

Structure project cleanly:

/app
    main.py
    routes/
    services/
    templates/
    static/
        css/
        js/

------------------------------------------------------------
FRONTEND REQUIREMENTS
------------------------------------------------------------

Use:

- TailwindCSS CDN
- Clean minimal modern design
- Centered layout
- Chat bubbles (user right, assistant left)
- Smooth transitions
- Mobile-first responsive layout

Main elements:

- Language selector
- Single large circular main button
- Chat container
- Hidden audio blob storage

Button must visually change:
- Color
- Icon
- Label

------------------------------------------------------------
MICROPHONE IMPLEMENTATION
------------------------------------------------------------

Use:

navigator.mediaDevices.getUserMedia
MediaRecorder API

Requirements:

- Handle permission request
- Handle stop/start cleanly
- Convert audio to Blob
- Send via fetch() to backend
- Show recording indicator (visual)

Keep JS modular and clean.

------------------------------------------------------------
STYLE REQUIREMENTS
------------------------------------------------------------

Design should feel:

- Clean
- Modern
- Minimal
- Professional
- Similar to modern SaaS landing app
- Smooth spacing
- Rounded corners
- Subtle shadow

Do NOT build something that looks like a hackathon demo.

------------------------------------------------------------
OUTPUT REQUIREMENT
------------------------------------------------------------

Generate:

1. Complete folder structure
2. main.py
3. template files
4. JS file
5. Tailwind layout
6. Clear explanation of how everything connects

Code must be runnable.

Do not over-engineer.
Do not add unnecessary frameworks.
Keep it clean and understandable.

