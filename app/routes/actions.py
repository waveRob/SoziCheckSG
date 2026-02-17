from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from app.services.session import session_store

router = APIRouter()


@router.post("/initialize")
def initialize(request: Request, language: str = Form("de")) -> JSONResponse:
    session_id = request.cookies.get("session_id")
    session_id = session_store.get_or_create(session_id, language=language)
    state = session_store.get(session_id)
    state.initialized = True
    state.language = language
    if not state.chat:
        state.chat.append(
            {
                "role": "assistant",
                "content": "Willkommen! Die Unterhaltung wurde initialisiert.",
            }
        )

    response = JSONResponse(
        {
            "ok": True,
            "state": "recording",
            "chat": state.chat,
            "message": "Session initialized (scaffold).",
        }
    )
    response.set_cookie("session_id", session_id, httponly=True, samesite="lax")
    return response


@router.post("/upload-audio")
def upload_audio(request: Request, audio: UploadFile | None = None) -> JSONResponse:
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
    state.chat.append(
        {
            "role": "assistant",
            "content": "Audio processing is not implemented in Step 1 scaffold yet.",
        }
    )

    return JSONResponse(
        {
            "ok": True,
            "transcript": "",
            "assistant_response": "Audio processing placeholder.",
            "chat": state.chat,
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
