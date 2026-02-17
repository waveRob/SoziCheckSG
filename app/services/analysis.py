from __future__ import annotations

import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.services.chatbot import chatbot_service

ANALYSIS_PROMPT = (
    "Be the audit bot for Sozialhilfe Check St. Gallen. "
    "Answer TRUE only if the assistant already delivered a final outcome: "
    "(A) 'Ja, wahrscheinlich Anspruch' plus intake hint, (B) 'Möglicherweise Anspruch' "
    "plus intake hint, (C) 'Nein, das Einkommen ist zu hoch', or an allowed redirect such as "
    "referring the user to another authority because they live outside St. Gallen or seek "
    "another service. Reply FALSE whenever the conversation is still collecting data or no "
    "clear outcome exists. Respond with exactly TRUE or FALSE and nothing else."
)

SUMMARY_PROMPT = (
    "Du erstellst eine extrem kurze Sachübersicht für eine Behörde. "
    "Arbeite ausschließlich mit klaren Fakten aus dem Gespräch. "
    "Keine Erklärungen. Keine Höflichkeitsformeln. "
    "Keine Interpretation. "
    "Kein Bezug auf Gesprächsverlauf. "
    "Maximal eine sehr kurze Aussage oder wenige Stichpunkte."
)


def _remove_emojis(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F700-\U0001F77F"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF"
        "\U00002700-\U000027BF"
        "\U000024C2-\U0001F251"
        "*#]+"
        r"(?:[\u200d\ufe0f\U0001F3FB-\U0001F3FF])*",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text)


def _build_chat_text(chat_history: List[Dict[str, str]]) -> str:
    return "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_history[1:]])


def conversation_concluded(chat_history: List[Dict[str, str]], max_length: int = 30) -> bool:
    if len(chat_history) <= 2:
        return False

    messages = [
        {"role": "system", "content": ANALYSIS_PROMPT},
        {"role": "user", "content": _build_chat_text(chat_history)},
    ]

    completion = chatbot_service.client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_completion_tokens=max_length,
        temperature=0,
    )
    answer = (completion.choices[0].message.content or "").strip().lower()
    return answer.startswith("true")


def create_summary(chat_history: List[Dict[str, str]]) -> str:
    messages = [
        {"role": "system", "content": SUMMARY_PROMPT},
        {"role": "user", "content": _build_chat_text(chat_history)},
    ]

    completion = chatbot_service.client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_completion_tokens=200,
        temperature=0.2,
    )
    return (completion.choices[0].message.content or "").strip()


def _add_header_and_page_number(canvas, doc):
    canvas.saveState()
    page_num = canvas.getPageNumber()
    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(A4[0] / 2, 1 * cm, f"Seite {page_num}")

    if hasattr(doc, "logo_path") and doc.logo_path and os.path.exists(doc.logo_path):
        canvas.drawImage(doc.logo_path, 1 * cm, A4[1] - 3 * cm, width=3 * cm, height=3 * cm, preserveAspectRatio=True, mask="auto")

    canvas.line(1 * cm, A4[1] - 3.2 * cm, A4[0] - 1 * cm, A4[1] - 3.2 * cm)
    canvas.restoreState()


def create_analysis_pdf(msg_history: List[Dict[str, str]], target_language: str, logo_path: str = "app/static/images/logo_stgallen.png") -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d")
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=3.5 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    doc.logo_path = str(Path(logo_path))

    styles = getSampleStyleSheet()
    user_style = ParagraphStyle(name="UserChat", parent=styles["Normal"], alignment=TA_LEFT, fontSize=10, leading=13, spaceAfter=5, leftIndent=0)
    assistant_style = ParagraphStyle(name="AssistantChat", parent=styles["Normal"], alignment=TA_LEFT, fontSize=10, leading=13, spaceAfter=5, leftIndent=25)

    flow = [
        Paragraph(f"<b>Exportdatum:</b> {timestamp}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("<b>Sozialhilfe-Check St.Gallen</b>", styles["Heading2"]),
        Spacer(1, 12),
        Paragraph("<b>DEUTSCH</b>", styles["Heading3"]),
        Paragraph("<b>Übersicht:</b>"),
        Spacer(1, 8),
    ]

    summary = create_summary(msg_history)
    for line in summary.split("\n"):
        if line.strip():
            flow.append(Paragraph(line.strip(), styles["Normal"]))
            flow.append(Spacer(1, 4))

    flow.extend([Spacer(1, 12), Spacer(1, 12)])

    for msg in msg_history[2:]:
        text = _remove_emojis(msg["content"]).replace("\n", "<br/>")
        if target_language != "german":
            text = chatbot_service.translate_text(text, "de")
        if msg["role"] == "user":
            flow.append(Paragraph(f"<b>Beantragende:r:</b> {text}", user_style))
        else:
            flow.append(Paragraph(f"<b>Sozi-Bot:</b> {text}", assistant_style))

    flow.append(Spacer(1, 12))

    if target_language != "german":
        flow.append(Paragraph(f"<b>{target_language.capitalize()}</b>", styles["Heading3"]))
        for msg in msg_history[2:]:
            text = _remove_emojis(msg["content"]).replace("\n", "<br/>")
            if msg["role"] == "user":
                flow.append(Paragraph(f"<b>Beantragende:r:</b> {text}", user_style))
            else:
                flow.append(Paragraph(f"<b>Sozi-Bot:</b> {text}", assistant_style))
        flow.append(Spacer(1, 12))

    doc.build(flow, onFirstPage=_add_header_and_page_number, onLaterPages=_add_header_and_page_number)
    return path
