"""
tests/test_prompt_regression.py

Data-driven prompt regression harness for ai_query_parser.py.

Each test case lives in tests/fixtures/prompt_regression.jsonl.
The harness loads the JSONL at collection time, runs each prompt through
the rule-based parser (no OpenAI key), and asserts schema + field + rule
constraints.

Running:
    pytest tests/test_prompt_regression.py -v          # all cases, verbose
    pytest tests/test_prompt_regression.py::test_golden_never_regress -v  # golden only
    pytest -k "leaderboard"                             # filter by tag substring in ID

Adding a new case:
    Call add_regression_case() from the project root or paste a new JSON line
    directly into tests/fixtures/prompt_regression.jsonl.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from ai_query_parser import parse_natural_language_query
from query_engine import TEAM_METRICS_ALLOWLIST

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "prompt_regression.jsonl"

VALID_RESULT_TYPES = {"QUERY", "CLARIFY", "OUT_OF_SCOPE"}
VALID_CHART_TYPES  = {"leaderboard", "scatter", "compare"}
VALID_WINDOWS      = {"SEASON", "LAST_5", "LAST_10", "LAST_20"}


# ---------------------------------------------------------------------------
# Parser helper — always use rule-based path (no OpenAI key)
# ---------------------------------------------------------------------------

def _no_key_env() -> dict:
    return {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}


def _parse_no_key(query: str) -> dict:
    with patch.dict(os.environ, _no_key_env(), clear=True):
        return parse_natural_language_query(query)


# ---------------------------------------------------------------------------
# JSONL loader — runs at collection time; malformed JSON = loud collection error
# ---------------------------------------------------------------------------

def _load_cases() -> list[dict]:
    cases = []
    with open(FIXTURES_PATH, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"prompt_regression.jsonl line {lineno}: {exc}") from exc
    return cases


_ALL_CASES    = _load_cases()
_GOLDEN_CASES = [c for c in _ALL_CASES if "golden" in c.get("tags", [])]


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------

def _rule_valid_query_schema(r: dict) -> None:
    assert r.get("result_type") in VALID_RESULT_TYPES, \
        f"result_type {r.get('result_type')!r} not in {VALID_RESULT_TYPES}"
    assert "_debug" in r, "_debug key missing"
    assert isinstance(r["_debug"], dict), "_debug must be a dict"
    required_debug = {"openai_used", "fallback_used", "fallback_reason"}
    assert required_debug <= r["_debug"].keys(), \
        f"_debug missing keys: {required_debug - r['_debug'].keys()}"


def _rule_valid_chart_type(r: dict) -> None:
    ct = r.get("chart_type")
    assert ct in VALID_CHART_TYPES, f"chart_type {ct!r} not in {VALID_CHART_TYPES}"


def _rule_valid_metric(r: dict) -> None:
    m = r.get("metric")
    assert m is not None, "metric key missing"
    assert m in TEAM_METRICS_ALLOWLIST, \
        f"metric {m!r} not in allowlist {sorted(TEAM_METRICS_ALLOWLIST)}"


def _rule_valid_window(r: dict) -> None:
    w = r.get("window")
    assert w in VALID_WINDOWS, f"window {w!r} not in {VALID_WINDOWS}"


def _rule_has_message(r: dict) -> None:
    msg = r.get("message")
    assert msg is not None, "message field missing"
    assert isinstance(msg, str) and len(msg.strip()) > 0, \
        "message must be a non-empty string"


def _rule_no_metric_leak(r: dict) -> None:
    """OUT_OF_SCOPE results must not contain chart_type — the OOS guard short-circuits before parse."""
    assert "chart_type" not in r, \
        f"OUT_OF_SCOPE result leaked chart_type={r.get('chart_type')!r}"


def _rule_valid_top_n(r: dict) -> None:
    top_n = r.get("top_n")
    if top_n is not None:
        assert isinstance(top_n, int) and top_n >= 1, \
            f"top_n must be int >= 1, got {top_n!r}"


def _rule_teams_min_two(r: dict) -> None:
    teams = r.get("teams")
    assert teams is not None, "teams field missing"
    assert isinstance(teams, list) and len(teams) >= 2, \
        f"compare requires >= 2 teams, got {teams!r}"


_RULES: dict[str, Any] = {
    "valid_query_schema": _rule_valid_query_schema,
    "valid_chart_type":   _rule_valid_chart_type,
    "valid_metric":       _rule_valid_metric,
    "valid_window":       _rule_valid_window,
    "has_message":        _rule_has_message,
    "no_metric_leak":     _rule_no_metric_leak,
    "valid_top_n":        _rule_valid_top_n,
    "teams_min_two":      _rule_teams_min_two,
}


# ---------------------------------------------------------------------------
# Core assertion helper (shared by both parametrize functions)
# ---------------------------------------------------------------------------

def _assert_case(case: dict, result: dict) -> None:
    exp = case["expected"]
    cid = case["id"]

    # 1. result_type
    assert result.get("result_type") == exp["result_type"], (
        f"[{cid}] result_type: got {result.get('result_type')!r}, "
        f"expected {exp['result_type']!r}"
    )

    # 2. exact-match fields
    for field, expected_val in exp.get("fields", {}).items():
        actual_val = result.get(field)
        assert actual_val == expected_val, (
            f"[{cid}] field {field!r}: got {actual_val!r}, expected {expected_val!r}"
        )

    # 3. required keys must be present
    for key in exp.get("required_keys", []):
        assert key in result, f"[{cid}] required key {key!r} missing from result"

    # 4. forbidden keys must be absent
    for key in exp.get("forbidden_keys", []):
        assert key not in result, f"[{cid}] forbidden key {key!r} present in result"

    # 5. named rules
    for rule_name in exp.get("rules", []):
        rule_fn = _RULES.get(rule_name)
        assert rule_fn is not None, f"[{cid}] unknown rule {rule_name!r}"
        rule_fn(result)


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case", _ALL_CASES, ids=lambda c: c["id"])
def test_prompt_regression(case: dict) -> None:
    """Run every JSONL case through the rule-based parser and assert all constraints."""
    result = _parse_no_key(case["prompt"])
    _assert_case(case, result)


@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=lambda c: c["id"])
def test_golden_never_regress(case: dict) -> None:
    """
    Golden cases run as a second dedicated parametrize block so CI shows them as a
    separate named failure group — making regressions immediately visible in PR checks.
    """
    result = _parse_no_key(case["prompt"])
    _assert_case(case, result)


# ---------------------------------------------------------------------------
# Helper to extend the dataset programmatically
# ---------------------------------------------------------------------------

def add_regression_case(
    case_id: str,
    prompt: str,
    result_type: str,
    fields: dict | None = None,
    required_keys: list[str] | None = None,
    forbidden_keys: list[str] | None = None,
    rules: list[str] | None = None,
    tags: list[str] | None = None,
) -> None:
    """
    Append a new regression case to tests/fixtures/prompt_regression.jsonl.

    Usage (from the project root):
        python -c "
        from tests.test_prompt_regression import add_regression_case
        add_regression_case(
            'my_new_pace_case',
            'show me pace leaders for 2024-25',
            result_type='QUERY',
            fields={'metric': 'PACE', 'season': '2024-25'},
            required_keys=['chart_type', 'metric', 'season'],
            rules=['valid_query_schema', 'valid_metric'],
            tags=['leaderboard', 'season'],
        )
        "
    """
    entry = {
        "id": case_id,
        "prompt": prompt,
        "expected": {
            "result_type": result_type,
            "fields": fields or {},
            "required_keys": required_keys or [],
            "forbidden_keys": forbidden_keys or [],
            "rules": rules or ["valid_query_schema"],
        },
        "tags": tags or [],
    }
    with open(FIXTURES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"Added case {case_id!r} to {FIXTURES_PATH}")
