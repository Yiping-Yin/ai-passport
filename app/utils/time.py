"""Time helpers for consistent UTC timestamps."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return a naive UTC timestamp for current repo data contracts."""
    return datetime.now(UTC).replace(tzinfo=None)
