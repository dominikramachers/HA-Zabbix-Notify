"""Validation of the notification icon option."""

from __future__ import annotations

import re

# Icon name (mdi:server), path on this Home Assistant (/local/logo.png), web
# address (https://...) or embedded image (data:image/png;base64,...).
# Same rules as the "type_icon" field of the notification center.
_ICON_REF = re.compile(
    r"^(?:[a-z][a-z0-9_-]*:[a-z0-9_.-]+"
    r"|/(?!/)\S*"
    r"|https?://\S+"
    r"|data:image/(?:png|jpeg|gif|webp|svg\+xml);base64,[A-Za-z0-9+/=]+)$"
)
MAX_ICON_LENGTH = 20000


def is_valid_icon(value: str) -> bool:
    """True for an empty value (category icon) or an accepted icon reference."""
    text = value.strip()
    if not text:
        return True
    return len(text) <= MAX_ICON_LENGTH and bool(_ICON_REF.match(text))
