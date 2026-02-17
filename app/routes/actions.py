from pydantic import BaseModel

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from app.services.chatbot import chatbot_service
from app.services.config import DEFAULT_LANGUAGE, LANGUAGE_CONFIG
from app.services.session import session_store

router = APIRouter()


class SendMessagePayload(BaseModel):
    text: str


class QuickRepliesPayload(BaseModel):
    text: str


@router.post("/initialize")
def initialize(request: Request, language: str = Form(DEFAULT_LANGUAGE)) -> JSONResponse:
    language = language if language in LANGUAGE_CONFIG else DEFAULT_LANGUAGE

    session_id = request.cookies.get("session_id")
    session_id = session_store.get_or_create(session_id, language=language)
    state = session_store.get(session_id)
    state.initialized = True
    state.language = language

    system_messages, intro_text, _ = chatbot_service.initialize_conversation(language)
    state.chat = system_messages

    audio_base64, audio_mime = chatbot_service.text_to_speech(intro_text, language)

    response = JSONResponse(
        {
            "ok": True,
            "state": "idle",
            "message": "Initialized. Ready to record.",
            "intro": intro_text,
            "intro_audio": audio_base64,
            "intro_audio_mime": audio_mime,
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

    transcription = chatbot_service.transcribe_audio(audio_bytes=audio_bytes, filename=audio.filename or "recording.webm")
    return JSONResponse({"ok": True, "transcription": transcription})


@router.post("/send-message")
def send_message(request: Request, payload: SendMessagePayload) -> JSONResponse:
    session_id = request.cookies.get("session_id")
    if not session_id:
        return JSONResponse({"ok": False, "error": "Session not initialized."}, status_code=400)

    state = session_store.get(session_id)
    text = payload.text.strip()
    if not text:
        return JSONResponse({"ok": False, "error": "Text is required."}, status_code=400)

    state.chat.append({"role": "user", "content": text})
    assistant_reply = chatbot_service.generate_reply(state.chat)
    state.chat.append({"role": "assistant", "content": assistant_reply})

    audio_base64, audio_mime = chatbot_service.text_to_speech(assistant_reply, state.language)

    return JSONResponse(
        {
            "ok": True,
            "reply": assistant_reply,
            "reply_audio": audio_base64,
            "reply_audio_mime": audio_mime,
        }
    )


@router.post("/quick-replies")
def quick_replies(request: Request, payload: QuickRepliesPayload) -> JSONResponse:
    session_id = request.cookies.get("session_id")
    if not session_id:
        return JSONResponse({"ok": False, "error": "Session not initialized."}, status_code=400)

    state = session_store.get(session_id)
    replies = chatbot_service.suggest_short_answers(payload.text, state.language)

    return JSONResponse({"ok": True, "quick_replies": replies})


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
