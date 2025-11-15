"""Utility for coordinating interactive prompts between parser and Telegram bot."""
from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

try:  # pragma: no cover - Windows fallback
    import fcntl as _fcntl  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    _fcntl = None  # type: ignore

fcntl = cast(Any, _fcntl)


class PromptManager:
    """File-based storage for pending prompts and user responses."""

    def __init__(self, storage_path: Optional[Path] = None, max_prompts: int = 200) -> None:
        base_dir = Path(__file__).resolve().parent
        self.storage_path = storage_path or (base_dir / "prompt_state.json")
        self.max_prompts = max_prompts
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _locked_state(self, write_back: bool = True) -> Any:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "a+", encoding="utf-8") as handle:
            if fcntl:
                fcntl.flock(handle, fcntl.LOCK_EX)
            handle.seek(0)
            data = handle.read()
            if not data:
                state: Dict[str, List[Dict[str, Any]]] = {"prompts": []}
            else:
                handle.seek(0)
                state = json.load(handle)
            yield state
            if write_back:
                # Ensure only recent prompts are kept to avoid unbounded growth
                prompts = state.get("prompts", [])
                state["prompts"] = prompts[-self.max_prompts :]
                handle.seek(0)
                handle.truncate()
                json.dump(state, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            if fcntl:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def create_prompt(self, prompt_text: str, timeout: int | float | None) -> str:
        prompt_id = uuid.uuid4().hex[:8].upper()
        created_at = time.time()
        with self._locked_state() as state:
            state.setdefault("prompts", []).append(
                {
                    "id": prompt_id,
                    "prompt": prompt_text,
                    "created_at": created_at,
                    "status": "waiting",
                    "timeout": timeout,
                    "response": None,
                }
            )
        return prompt_id

    def get_prompt(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        with self._locked_state(write_back=False) as state:
            prompts = state.get("prompts", [])
            for prompt in prompts:
                if prompt.get("id") == prompt_id:
                    return prompt
        return None

    def get_oldest_waiting_prompt(self) -> Optional[Dict[str, Any]]:
        """Получить самый НОВЫЙ (последний) ожидающий промпт, игнорируя истекшие."""
        current_time = time.time()
        with self._locked_state(write_back=False) as state:
            valid_prompts = []
            for prompt in state.get("prompts", []):
                if prompt.get("status") == "waiting":
                    # Проверяем, не истек ли промпт по времени
                    timeout = prompt.get("timeout")
                    created_at = prompt.get("created_at", 0)
                    if timeout and (current_time - created_at) > timeout:
                        # Промпт истек, но статус еще не обновлен - пропускаем
                        continue
                    valid_prompts.append(prompt)
            
            # Возвращаем самый НОВЫЙ (последний по времени создания)
            if valid_prompts:
                return max(valid_prompts, key=lambda p: p.get("created_at", 0))
        return None

    def set_response(self, prompt_id: str, response_text: str, user: Optional[str] = None) -> bool:
        responded_at = time.time()
        with self._locked_state() as state:
            for prompt in state.get("prompts", []):
                if prompt.get("id") == prompt_id and prompt.get("status") == "waiting":
                    prompt["status"] = "answered"
                    prompt["response"] = {
                        "text": response_text,
                        "user": user,
                        "responded_at": responded_at,
                    }
                    return True
        return False

    def set_response_for_oldest(self, response_text: str, user: Optional[str] = None) -> Optional[str]:
        responded_at = time.time()
        captured_id: Optional[str] = None
        with self._locked_state() as state:
            for prompt in state.get("prompts", []):
                if prompt.get("status") == "waiting":
                    prompt["status"] = "answered"
                    prompt["response"] = {
                        "text": response_text,
                        "user": user,
                        "responded_at": responded_at,
                    }
                    captured_id = prompt.get("id")
                    break
        return captured_id

    def mark_expired(self, prompt_id: str) -> None:
        with self._locked_state() as state:
            for prompt in state.get("prompts", []):
                if prompt.get("id") == prompt_id and prompt.get("status") == "waiting":
                    prompt["status"] = "expired"
                    prompt["response"] = None
                    break
    
    def cleanup_expired_prompts(self) -> int:
        """Автоматически помечает истекшие промпты как expired."""
        current_time = time.time()
        expired_count = 0
        with self._locked_state() as state:
            for prompt in state.get("prompts", []):
                if prompt.get("status") == "waiting":
                    timeout = prompt.get("timeout")
                    created_at = prompt.get("created_at", 0)
                    if timeout and (current_time - created_at) > timeout:
                        prompt["status"] = "expired"
                        prompt["response"] = None
                        expired_count += 1
        return expired_count

    def has_waiting_prompts(self) -> bool:
        with self._locked_state(write_back=False) as state:
            return any(prompt.get("status") == "waiting" for prompt in state.get("prompts", []))

    def get_response_text(self, prompt_id: str) -> Optional[str]:
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            return None
        response = prompt.get("response")
        if response:
            return response.get("text")
        return None
