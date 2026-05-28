"""LLM Gateway — manages OpenAI-compatible client lifecycle."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SETTINGS_FILE = Path(__file__).resolve().parent.parent.parent / "llm_settings.json"

DEFAULT_PROFILES = {
    "openai": {
        "provider": "openai",
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
    },
    "deepseek": {
        "provider": "deepseek",
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "moonshot": {
        "provider": "moonshot",
        "name": "Moonshot (Kimi)",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
    },
    "zhipu": {
        "provider": "zhipu",
        "name": "Zhipu (GLM)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-plus",
    },
    "custom": {
        "provider": "custom",
        "name": "Custom",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
    },
}


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"profiles": [], "active_profile_id": None}


def save_settings(data: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_active_profile() -> Optional[dict]:
    settings = load_settings()
    active_id = settings.get("active_profile_id")
    for p in settings.get("profiles", []):
        if p.get("id") == active_id:
            return p
    return None


class LLMGateway:
    """Manages the OpenAI-compatible client."""

    def __init__(self):
        self._client = None
        self._model = None
        self.refresh_client()

    def refresh_client(self) -> bool:
        profile = get_active_profile()
        if not profile or not profile.get("api_key"):
            self._client = None
            self._model = None
            return False
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=profile["api_key"],
                base_url=profile.get("base_url", "https://api.openai.com/v1"),
            )
            self._model = profile.get("model", "gpt-4o")
            return True
        except ImportError:
            logger.warning("openai package not installed")
            self._client = None
            self._model = None
            return False

    @property
    def client(self):
        return self._client

    @property
    def model(self) -> str:
        return self._model or "gpt-4o"

    @property
    def ready(self) -> bool:
        return self._client is not None


# Singleton
llm_gateway = LLMGateway()
