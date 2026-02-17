from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.config import DEFAULT_LANGUAGE, LANGUAGE_CONFIG

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    language_options = [
        {"value": key, "label": f"{cfg['flag']} {cfg['label']}"}
        for key, cfg in LANGUAGE_CONFIG.items()
    ]
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "page_title": "Sozialhilfe-Check",
            "default_language": DEFAULT_LANGUAGE,
            "language_options": language_options,
        },
    )
