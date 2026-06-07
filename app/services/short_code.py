import hashlib
import re
import secrets
from urllib.parse import urlparse

from app.core.config import settings

BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
CUSTOM_ALIAS_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
RESERVED_CODES = frozenset(
    {
        "health",
        "metrics",
        "urls",
        "shorten",
        "docs",
        "redoc",
        "openapi.json",
        "favicon.ico",
    }
)


def generate_base62_code(length: int | None = None) -> str:
    code_length = length or settings.short_code_length
    return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(code_length))


def validate_custom_alias(alias: str) -> None:
    if not alias or len(alias) > 64:
        raise ValueError("Custom alias must be 1-64 characters")
    if alias.lower() in RESERVED_CODES:
        raise ValueError("Custom alias is reserved")
    if not CUSTOM_ALIAS_PATTERN.match(alias):
        raise ValueError("Custom alias may only contain letters, numbers, hyphens, and underscores")


def validate_long_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must use http or https scheme")
    if not parsed.netloc:
        raise ValueError("URL must include a host")
    return url


def hash_ip(ip: str) -> str:
    digest = hashlib.sha256(f"{settings.ip_hash_salt}:{ip}".encode()).hexdigest()
    return digest[:32]


def generate_unique_code(existing_codes: set[str], length: int | None = None) -> str:
    for _ in range(10):
        code = generate_base62_code(length)
        if code not in existing_codes:
            return code
    raise RuntimeError("Unable to generate unique short code after retries")
