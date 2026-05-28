"""Settings routes — LLM provider config."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..services.llm_gateway import (
    DEFAULT_PROFILES,
    load_settings,
    save_settings,
    llm_gateway,
)

router = APIRouter(tags=["settings"])


@router.get("/settings")
async def get_settings():
    return load_settings()


@router.put("/settings")
async def update_settings(req: dict):
    profiles = req.get("profiles", [])
    for p in profiles:
        if "id" not in p:
            p["id"] = p.get("provider", "custom") + "_" + str(hash(p.get("name", "")))
    data = {
        "profiles": profiles,
        "active_profile_id": req.get("active_profile_id"),
    }
    save_settings(data)
    llm_gateway.refresh_client()
    return {"status": "ok", "ready": llm_gateway.ready}


@router.get("/settings/presets")
async def get_presets():
    return list(DEFAULT_PROFILES.values())


@router.post("/settings/test")
async def test_connection(req: dict):
    """Test an LLM connection with the given profile parameters."""
    api_key = req.get("api_key", "")
    base_url = req.get("base_url", "https://api.openai.com/v1")
    model = req.get("model", "gpt-4o")

    if not api_key:
        return {"ok": False, "error": "API key is required"}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
            stream=False,
        )
        choice = response.choices[0]
        return {"ok": True, "model": model, "response": choice.message.content}
    except ImportError:
        return {"ok": False, "error": "openai package not installed"}
    except Exception as e:
        msg = str(e)
        if api_key in msg:
            msg = msg.replace(api_key, "***")
        return {"ok": False, "error": msg}


@router.get("/settings/status")
async def settings_status():
    profile = None
    settings = load_settings()
    active_id = settings.get("active_profile_id")
    for p in settings.get("profiles", []):
        if p.get("id") == active_id:
            profile = {"provider": p.get("provider"), "name": p.get("name"), "model": p.get("model")}
            break
    return {
        "ready": llm_gateway.ready,
        "active_profile": profile,
    }
