"""
Tests for the public /api/v1/eval-results/latest endpoint.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from app.main import app
from app.routes.eval_results import _EVAL_RESULTS_PATH


def test_latest_returns_200_with_expected_shape(test_client):
    resp = test_client.get("/api/v1/eval-results/latest")
    assert resp.status_code == 200
    data = resp.json()

    assert "latest" in data
    latest = data["latest"]
    assert "date" in latest
    assert "git_sha" in latest
    assert "precision" in latest
    assert "recall" in latest
    assert "f1_score" in latest
    assert "disagreement_rate" in latest
    assert "prompt_version" in latest

    assert isinstance(latest["precision"], (int, float))
    assert isinstance(latest["recall"], (int, float))
    assert isinstance(latest["f1_score"], (int, float))
    assert latest["precision"] >= 0
    assert latest["precision"] <= 1

    assert "threshold" in data
    assert data["threshold"]["precision"] == 0.95
    assert data["threshold"]["recall"] == 0.95


def test_latest_no_auth_required(test_client):
    """No auth header — endpoint is public (no auth dependency)."""
    resp = test_client.get("/api/v1/eval-results/latest", headers={})
    assert resp.status_code == 200


def test_latest_503_on_missing_file(test_client):
    with patch.object(type(_EVAL_RESULTS_PATH), "read_text", side_effect=FileNotFoundError):
        resp = test_client.get("/api/v1/eval-results/latest")
    assert resp.status_code == 503
    assert "error" in resp.json()


def test_latest_503_on_empty_table(test_client, tmp_path):
    empty = tmp_path / "EMPTY.md"
    empty.write_text("# No table here\n\nJust a paragraph.\n")
    with patch("app.routes.eval_results._EVAL_RESULTS_PATH", empty):
        resp = test_client.get("/api/v1/eval-results/latest")
    assert resp.status_code == 503
    assert "parseable" in resp.json()["error"].lower()
