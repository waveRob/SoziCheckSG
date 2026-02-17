from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import yaml
from dotenv import load_dotenv
from google.cloud import texttospeech
from google.oauth2 import service_account
from openai import OpenAI

from app.services.config import DEFAULT_LANGUAGE, LANGUAGE_CONFIG, SCENARIO_NAME


class ChatbotService:
    def __init__(self) -> None:
        load_dotenv()
        self._openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        with open(Path("prompts.yaml"), "r", encoding="utf-8") as fh:
            self._scenarios = yaml.safe_load(fh)

    def initialize_conversation(self, language_key: str) -> Tuple[List[Dict[str, str]], str, str]:
        role_text = self._scenarios[SCENARIO_NAME]["role"]
        context_text = self._scenarios[SCENARIO_NAME]["context"]
        target = LANGUAGE_CONFIG.get(language_key, LANGUAGE_CONFIG[DEFAULT_LANGUAGE])

        translated_role = self.translate_text(role_text, target["code"])
        translated_context = self.translate_text(context_text, target["code"]) if language_key != "german" else context_text

        return ([{"role": "system", "content": translated_role}], translated_context, translated_role)

    @property
    def client(self) -> OpenAI:
        return self._openai

    def transcribe_audio(self, audio_bytes: bytes, filename: str) -> str:
        file_obj = io.BytesIO(audio_bytes)
        file_obj.name = filename
        transcript = self._openai.audio.transcriptions.create(model="gpt-4o-mini-transcribe", file=file_obj)
        return transcript.text.strip()

    def generate_reply(self, messages: List[Dict[str, str]]) -> str:
        completion = self._openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_completion_tokens=160,
        )
        return (completion.choices[0].message.content or "").strip()

    def translate_text(self, text: str, target_language_code: str) -> str:
        messages = [
            {"role": "system", "content": "You are a translation assistant. Return only the translated text."},
            {
                "role": "user",
                "content": f"Translate the following text into {target_language_code}. Return only translation:\n\n{text}",
            },
        ]
        completion = self._openai.chat.completions.create(model="gpt-4o-mini", messages=messages, max_completion_tokens=300)
        return (completion.choices[0].message.content or text).strip()


    def suggest_short_answers(self, text: str, language_key: str) -> List[str]:
        cleaned_text = text.strip()
        if not cleaned_text:
            return []

        language_label = LANGUAGE_CONFIG.get(language_key, LANGUAGE_CONFIG[DEFAULT_LANGUAGE])["label"]
        messages = [
            {
                "role": "system",
                "content": (
                    "You analyze a single assistant message and decide whether short quick-reply answers are helpful. "
                    "Return JSON only, with schema: {\"answers\": [string, ...]}. "
                    "Rules: max 4 answers, each <= 30 chars, no duplicates, no punctuation-only entries. "
                    "If no clear short answers exist, return {\"answers\": []}."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Language: {language_label}.\n"
                    f"Assistant message:\n{cleaned_text}\n\n"
                    "Return only JSON."
                ),
            },
        ]

        try:
            completion = self._openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_completion_tokens=120,
                temperature=0,
            )
        except Exception:
            return []

        raw = (completion.choices[0].message.content or "").strip()
        if not raw:
            return []

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return []

        answers = payload.get("answers", [])
        if not isinstance(answers, list):
            return []

        normalized = []
        for item in answers:
            if not isinstance(item, str):
                continue
            value = item.strip()
            if not value:
                continue
            if len(value) > 30:
                continue
            normalized.append(value)

        return list(dict.fromkeys(normalized))[:4]

    def text_to_speech(self, text: str, language_key: str) -> Tuple[str | None, str | None]:
        credentials = os.getenv("GOOGLE_CREDENTIALS")
        if not credentials:
            return None, None

        creds_payload = json.loads(credentials.replace("\n", "\\n"))
        creds = service_account.Credentials.from_service_account_info(creds_payload)
        tts_client = texttospeech.TextToSpeechClient(credentials=creds)

        config = LANGUAGE_CONFIG.get(language_key, LANGUAGE_CONFIG[DEFAULT_LANGUAGE])
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(language_code=config["speech_locale"])
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

        response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        if not response.audio_content:
            return None, None

        encoded = base64.b64encode(response.audio_content).decode("utf-8")
        return encoded, "audio/mpeg"


chatbot_service = ChatbotService()
