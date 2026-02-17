from pydantic import BaseModel

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse

from app.services.session import session_store

router = APIRouter()


class UploadPayload(BaseModel):
    text: str | None = None


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
            "state": "recording",
            "message": "Initialized. You can speak now.",
        }
    )
    response.set_cookie("session_id", session_id, httponly=True, samesite="lax")
    return response


@router.post("/upload-audio")
def upload_audio(request: Request, payload: UploadPayload) -> JSONResponse:
    session_id = request.cookies.get("session_id")
    if not session_id:
        return JSONResponse(
            {
                "ok": False,
                "error": "Session not initialized.",
            },
            status_code=400,
        )

    state = session_store.get(session_id)
    text = (payload.text or "").strip()
    if not text:
        return JSONResponse({"ok": False, "error": "No text provided."}, status_code=400)

    assistant_reply = f"Stub reply ({state.language}): I received '{text}'."

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
