"""Regression tests for the multi-turn negotiation ledger bug.

Background
----------
``NegotiationScenario`` exposes ``market_reference_price`` and the other
per-line-item pricing fields as convenience shims that read from
``line_items[0]``. These were originally plain ``@property`` methods, which
Pydantic v2 *omits* from ``model_dump()``. ``session_manager`` serialises the
scenario via ``model_dump()`` and the mock LLM reads ``scenario[...]`` back out,
so every negotiation turn after the initial offer raised
``KeyError: 'market_reference_price'`` and the turn was aborted.

The result: the buyer's opening offer was still recorded, but no subsequent
turn ever produced a message or a ledger entry. These tests lock in that a
multi-turn session records *more than one* message/ledger entry.
"""
import pytest

from app.models import DEFAULT_SCENARIO, NegotiationScenario, NegotiationSessionStatus
from app.session_manager import session_manager
from app.db import load_ledger_entries


# Pricing fields that must survive serialisation for the mock LLM to run a turn.
_PRICING_FIELDS = (
    "market_reference_price",
    "quantity",
    "buyer_target_price",
    "buyer_budget_cap",
    "seller_asking_price",
    "seller_floor_price",
    "product_name",
)


def test_scenario_model_dump_includes_pricing_fields():
    """model_dump() must include the line-item-derived pricing shims.

    Guards the exact failure mode: a plain @property is dropped by Pydantic,
    so a round-trip through model_dump() would miss these keys.
    """
    dumped = DEFAULT_SCENARIO.model_dump()
    for field in _PRICING_FIELDS:
        assert field in dumped, f"{field!r} missing from NegotiationScenario.model_dump()"

    # And the values must mirror the first line item (single source of truth).
    item0 = DEFAULT_SCENARIO.line_items[0]
    assert dumped["market_reference_price"] == item0.market_reference_price
    assert dumped["buyer_budget_cap"] == item0.buyer_budget_cap
    assert dumped["seller_floor_price"] == item0.seller_floor_price
    assert dumped["quantity"] == item0.quantity
    assert dumped["product_name"] == item0.product_name


def test_scenario_model_dump_survives_json_round_trip():
    """A JSON round-trip (as persisted/loaded by the DB) keeps the pricing keys."""
    reloaded = NegotiationScenario.model_validate_json(DEFAULT_SCENARIO.model_dump_json())
    dumped = reloaded.model_dump()
    for field in _PRICING_FIELDS:
        assert field in dumped, f"{field!r} lost after JSON round-trip"


@pytest.mark.asyncio
async def test_multi_turn_session_produces_multiple_ledger_entries():
    """A multi-turn mock session must record more than just the initial offer.

    Before the fix, turns after the opening offer crashed with a KeyError, so
    the session produced exactly one message and (at most) one ledger entry.
    """
    session = await session_manager.create_session(provider="mock")
    await session_manager.start_session(session.session_id)

    # Run several negotiation turns beyond the opening offer.
    await session_manager.process_turn(session.session_id, max_turns=4)

    messages = await session_manager.get_messages(session.session_id)
    assert len(messages) > 1, (
        "Expected the initial offer plus at least one negotiation turn, "
        f"got {len(messages)} message(s) — turns after the opening offer failed."
    )

    ledger_entries = await load_ledger_entries(session.session_id)
    assert len(ledger_entries) > 1, (
        "Expected more than one ledger entry for a multi-turn session, "
        f"got {len(ledger_entries)} — subsequent turns were never laddered."
    )

    # Every persisted message should be laddered into the hash chain.
    assert len(ledger_entries) == len(messages)

    updated = await session_manager.get_session(session.session_id)
    assert updated.status == NegotiationSessionStatus.COMPLETED
