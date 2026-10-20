"""Endpoint model names shared by V23 and V23.2."""
from urllib.parse import urlsplit

from .facts import require


MODELS = {
    "http://llm-proxy.intra.xiaojukeji.com": "deepseek-v4.1-flash",
    "https://api.deepseek.com": "deepseek-flash",
}


def model_for_endpoint(base_url, fallback=None):
    """Known endpoints override old model names; other endpoints need a model."""
    parsed = urlsplit(base_url)
    require(parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username
            and not parsed.password and not parsed.query and not parsed.fragment, "Invalid API base URL")
    origin = f"{parsed.scheme}://{parsed.netloc}"
    model = MODELS.get(origin) if parsed.path.rstrip("/") in {"", "/v1"} else None
    model = model or fallback
    require(bool(model), "Specify the actual endpoint model with --model")
    return model


def route_call_config(config, base_url):
    """Copy a call configuration, preserving all non-routing parameters."""
    return {**config, "endpoint": base_url.rstrip("/") + "/chat/completions",
            "model": model_for_endpoint(base_url, config.get("model"))}
