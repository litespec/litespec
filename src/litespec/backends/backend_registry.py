"""Backend registry (Phase 6)."""

from __future__ import annotations

from litespec.backends.backend_protocol import Backend
from litespec.backends.creusot_backend import CreusotBackend
from litespec.backends.kani_backend import KaniBackend
from litespec.backends.rem_backend import RemBackend
from litespec.backends.smack_backend import SmackBackend
from litespec.backends.verus_backend import VerusBackend

_REGISTRY: dict[str, Backend] = {
    b.name: b for b in [VerusBackend(), KaniBackend(), SmackBackend(), RemBackend(), CreusotBackend()]
}


def get_backend(name: str) -> Backend:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown backend {name!r}") from None


def all_backends() -> list[Backend]:
    return list(_REGISTRY.values())


def backend_names() -> list[str]:
    return list(_REGISTRY.keys())
