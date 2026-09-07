from config import settings


def build_client_url(path: str) -> str:
    origin = settings.client_origin.rstrip("/")
    normalized = path if path.startswith("/") else f"/{path}"
    return f"{origin}{normalized}"


def build_api_url(path: str) -> str:
    prefix = settings.api_prefix.rstrip("/")
    normalized = path if path.startswith("/") else f"/{path}"
    return build_client_url(f"{prefix}{normalized}")
