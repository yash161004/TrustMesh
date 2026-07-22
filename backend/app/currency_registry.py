"""
TrustMesh Currency Registry — config-driven currency metadata.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CurrencyMeta:
    code: str
    symbol: str
    decimal_precision: int


_DEFAULT_METADATA: dict[str, CurrencyMeta] = {
    "USD": CurrencyMeta("USD", "$", 2),
    "EUR": CurrencyMeta("EUR", "\u20ac", 2),
    "GBP": CurrencyMeta("GBP", "\u00a3", 2),
    "INR": CurrencyMeta("INR", "\u20b9", 2),
    "JPY": CurrencyMeta("JPY", "\u00a5", 0),
}

_DEFAULT_CODES = ["USD", "EUR", "GBP", "INR", "JPY"]


class CurrencyRegistry:
    def __init__(self, codes: list[str] | None = None) -> None:
        if codes is None:
            codes = self._codes_from_env()
        self._codes: list[str] = [c.strip().upper() for c in codes if c.strip()]
        self._metadata: dict[str, CurrencyMeta] = {
            code: _DEFAULT_METADATA.get(code, CurrencyMeta(code, code, 2))
            for code in self._codes
        }

    @staticmethod
    def _codes_from_env() -> list[str]:
        raw = os.environ.get("TRUSTMESH_CURRENCIES")
        if not raw:
            return list(_DEFAULT_CODES)
        return [c.strip().upper() for c in raw.split(",") if c.strip()]

    @property
    def codes(self) -> list[str]:
        return list(self._codes)

    def is_valid(self, code: str) -> bool:
        return code.strip().upper() in self._codes

    def meta(self, code: str) -> CurrencyMeta:
        code = code.strip().upper()
        if code not in self._metadata:
            raise KeyError(f"Unknown currency code: {code!r}")
        return self._metadata[code]

    def symbol(self, code: str) -> str:
        return self.meta(code).symbol

    def decimal_precision(self, code: str) -> int:
        return self.meta(code).decimal_precision

    def convert(self, amount: float, from_code: str, to_code: str) -> float:
        """Not implemented yet, intentionally — see NotImplementedError message."""
        raise NotImplementedError(
            "CurrencyRegistry.convert() has no FX rate source wired in yet. "
            "Do not assume 1:1 parity between currencies — wire a real "
            "rate provider before calling this."
        )


registry = CurrencyRegistry()
VALID_CURRENCIES: list[str] = registry.codes
