from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List
from uuid import uuid4


@dataclass
class SessionState:
    language: str = "de"
    initialized: bool = False
    chat: List[Dict[str, str]] = field(default_factory=list)


class SessionStore:
    """Simple in-memory session store scaffold for Step 1."""

    def __init__(self) -> None:
        self._store: Dict[str, SessionState] = {}
        self._lock = Lock()

    def new_session(self, language: str = "de") -> str:
        session_id = str(uuid4())
        with self._lock:
            self._store[session_id] = SessionState(language=language)
        return session_id

    def get_or_create(self, session_id: str | None, language: str = "de") -> str:
        if session_id:
            with self._lock:
                if session_id in self._store:
                    return session_id
        return self.new_session(language=language)

    def get(self, session_id: str) -> SessionState:
        with self._lock:
            return self._store[session_id]


session_store = SessionStore()
