from pydantic import BaseModel

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from app.services.session import session_store

router = APIRouter()


class SendMessagePayload(BaseModel):
    text: str


@router.post("/initialize")
def initialize(request: Request, language: str = Form("de")) -> JSONResponse:
    session_id = request.cookies.get("session_id")
    session_id = session_store.get_or_create(session_id, language=language)
    state = session_store.get(session_id)
    state.initialized = True
    state.language = language

    response = JSONResponse(
        {
            "ok": True,
            "state": "idle",
            "message": "Initialized. Ready to record.",
        }
    )
    response.set_cookie("session_id", session_id, httponly=True, samesite="lax")
    return response


@router.post("/upload-audio")
async def upload_audio(request: Request, audio: UploadFile = File(...)) -> JSONResponse:
    session_id = request.cookies.get("session_id")
    if not session_id:
        return JSONResponse({"ok": False, "error": "Session not initialized."}, status_code=400)

    state = session_store.get(session_id)
    if not state.initialized:
        return JSONResponse({"ok": False, "error": "Session not initialized."}, status_code=400)

    audio_bytes = await audio.read()
    if not audio_bytes:
        return JSONResponse({"ok": False, "error": "Uploaded audio is empty."}, status_code=400)

    return JSONResponse(
        {
            "ok": True,
            "transcription": f"stub transcription ({state.language})",
        }
    )


@router.post("/send-message")
def send_message(request: Request, payload: SendMessagePayload) -> JSONResponse:
    session_id = request.cookies.get("session_id")
    if not session_id:
        return JSONResponse({"ok": False, "error": "Session not initialized."}, status_code=400)

    state = session_store.get(session_id)
    text = payload.text.strip()
    if not text:
        return JSONResponse({"ok": False, "error": "Text is required."}, status_code=400)

    assistant_reply = f"stub assistant reply ({state.language}): received '{text}'"

    state.chat.append({"role": "user", "content": text})
    state.chat.append({"role": "assistant", "content": assistant_reply})

    return JSONResponse(
        {
            "ok": True,
            "reply": assistant_reply,
        }
    )


@router.post("/generate-pdf")
def generate_pdf(request: Request) -> JSONResponse:
    session_id = request.cookies.get("session_id")
    if not session_id:
        return JSONResponse({"ok": False, "error": "Session not initialized."}, status_code=400)

    return JSONResponse(
        {
            "ok": True,
            "message": "PDF generation scaffold endpoint ready.",
            "download_url": None,
        }
    )
