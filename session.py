"""会话：把 messages 存成 JSON，支持续聊。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SessionStore:
    def __init__(self, sessions_dir: str) -> None:
        self.dir = Path(sessions_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def new_id(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]

    def path_for(self, session_id: str) -> Path:
        return self.dir / f"{session_id}.json"

    def save(self, session_id: str, messages: list[dict[str, Any]]) -> Path:
        path = self.path_for(session_id)
        path.write_text(
            json.dumps({"id": session_id, "messages": messages}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def load(self, session_id: str) -> list[dict[str, Any]]:
        path = self.path_for(session_id)
        if not path.is_file():
            raise FileNotFoundError(f"会话不存在: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("messages") or [])
