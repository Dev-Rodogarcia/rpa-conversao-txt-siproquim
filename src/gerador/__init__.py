"""
Modulo de geracao de arquivos TXT no formato SIPROQUIM.
"""

from __future__ import annotations

__all__ = ["GeradorTXT"]


def __getattr__(name: str):
    if name == "GeradorTXT":
        from .txt_generator import GeradorTXT

        return GeradorTXT
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
