from __future__ import annotations

from scripts.run_neo4j_natural_retrieval_screen import _exact_sign_pvalue


def test_exact_sign_pvalue_uses_only_discordant_pairs() -> None:
    rows = [
        {"hits": {"left": True, "right": False}},
        {"hits": {"left": True, "right": False}},
        {"hits": {"left": False, "right": True}},
        {"hits": {"left": True, "right": True}},
    ]
    assert _exact_sign_pvalue(rows, "left", "right") == 0.5


def test_exact_sign_pvalue_is_one_when_no_pair_differs() -> None:
    rows = [{"hits": {"left": True, "right": True}}]
    assert _exact_sign_pvalue(rows, "left", "right") == 1.0
