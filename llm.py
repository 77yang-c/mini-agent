import httpx
from config import settings

def chat(message: list[dict],tools: list[dict] | None = None) -> dict:
    boby = {
        "model" : settings.model,
        "messages" : message
    }
    if tools:
        boby["tools"] = tools
        boby["tools_choice"] = "auto"
    
    r = httpx.post(
        f"{settings.base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization":f"Bearer{settings.api_key}",
            "Content-Type":"application/json",
        },
        json=boby,
        timeout=300.0,
    )
    return r.json()["choices"][0]["message"]