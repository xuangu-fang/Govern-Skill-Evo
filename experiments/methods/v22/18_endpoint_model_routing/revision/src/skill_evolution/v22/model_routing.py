"""Resolve endpoint-specific evolution models before freezing a new campaign."""

from urllib.parse import urlsplit, urlunsplit


PROFILE = "v22.endpoint_evolution.v1"
MODELS_BY_BASE_URL = {
    "http://llm-proxy.intra.xiaojukeji.com": "deepseek-v4-pro",
    "https://api.deepseek.com": "deepseek-v4.1-flash",
}


def evolution_route(base_url, declared_model):
    parsed = urlsplit(base_url.strip())
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("Expected an HTTP API base URL without credentials, query or fragment.")
    base = urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), "", ""))
    lookup = base[:-3] if base.endswith("/v1") else base
    return {"profile": PROFILE, "base_url": base, "declared_model": declared_model,
            "evolution": MODELS_BY_BASE_URL.get(lookup, declared_model)}
