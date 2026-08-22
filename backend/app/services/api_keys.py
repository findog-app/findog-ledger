import hashlib
import hmac
import secrets

from app.core.config import settings

API_KEY_PREFIX = "fdg_live_"
API_KEY_SAFE_PREFIX_LENGTH = 16


def generate_api_key() -> str:
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    """Return a deterministic keyed digest suitable for indexed key lookup."""
    return hmac.new(
        str(settings.SECRET_KEY).encode(), raw_key.encode(), hashlib.sha256
    ).hexdigest()


def key_prefix(raw_key: str) -> str:
    return raw_key[:API_KEY_SAFE_PREFIX_LENGTH]


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_api_key(raw_key), stored_hash)
