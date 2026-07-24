import os
import pytest
from app.currency_registry import CurrencyRegistry, CurrencyMeta, VALID_CURRENCIES, registry


def test_default_currencies():
    reg = CurrencyRegistry()
    assert reg.codes == ["USD", "EUR", "GBP", "INR", "JPY"]
    assert reg.is_valid("usd")
    assert reg.is_valid("JPY")
    assert not reg.is_valid("CAD")


def test_currency_metadata():
    reg = CurrencyRegistry()
    usd = reg.meta("USD")
    assert isinstance(usd, CurrencyMeta)
    assert usd.symbol == "$"
    assert usd.decimal_precision == 2

    jpy = reg.meta("JPY")
    assert jpy.symbol == "¥"
    assert jpy.decimal_precision == 0

    with pytest.raises(KeyError):
        reg.meta("AUD")


def test_env_var_override(monkeypatch):
    monkeypatch.setenv("TRUSTMESH_CURRENCIES", "USD, CAD, AUD")
    reg = CurrencyRegistry()
    assert reg.codes == ["USD", "CAD", "AUD"]
    assert reg.is_valid("CAD")
    assert reg.symbol("CAD") == "CAD"
    assert reg.decimal_precision("CAD") == 2


def test_convert_raises_not_implemented():
    reg = CurrencyRegistry()
    with pytest.raises(NotImplementedError) as exc_info:
        reg.convert(100.0, "USD", "EUR")
    assert "CurrencyRegistry.convert() has no FX rate source wired in yet" in str(exc_info.value)


def test_valid_currencies_export():
    assert isinstance(VALID_CURRENCIES, list)
    assert "USD" in VALID_CURRENCIES
    assert "INR" in VALID_CURRENCIES
