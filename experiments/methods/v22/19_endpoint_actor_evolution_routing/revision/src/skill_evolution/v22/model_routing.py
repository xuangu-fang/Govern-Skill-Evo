"""Resolve Actor and evolution models before freezing a new campaign."""

from urllib.parse import urlsplit, urlunsplit


PROFILE = "v22.endpoint_models.v2"
MODELS_BY_BASE_URL = {
    "http://llm-proxy.intra.xiaojukeji.com": {
        "actor": "deepseek-v4-flash", "evolution": "deepseek-v4-pro"},
    "https://api.deepseek.com": {
        "actor": "deepseek-flash", "evolution": "deepseek-flash"},
}


def model_route(base_url, declared_actor, declared_evolution):
    parsed = urlsplit(base_url.strip())
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("Expected an HTTP API base URL without credentials, query or fragment.")
    base = urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), "", ""))
    lookup = base[:-3] if base.endswith("/v1") else base
    declared = {"actor": declared_actor, "evolution": declared_evolution}
    return {"profile": PROFILE, "base_url": base, "declared_models": declared,
            **MODELS_BY_BASE_URL.get(lookup, declared)}
