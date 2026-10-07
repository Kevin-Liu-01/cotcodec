"""Zero-GPU priors reanalysis on synthetic lethe rows. Needs scipy only."""

from __future__ import annotations

import pytest

pytest.importorskip("scipy")

from scripts import q1_lethe_priors as priors  # noqa: E402


def _row(identifier: int, status: str = "gated", **gates: str) -> dict:
    statuses = {g: {"status": "pass"} for g in priors.CHANNELS}
    statuses.update({name.replace("_", "-"): {"status": s} for name, s in gates.items()})
    return {
        "id": str(identifier),
        "status": status,
        "op_class": "softmax",
        "gates": statuses,
        "output_aliasing": False,
    }


def test_union_and_intervals() -> None:
    rows = [
        _row(0, CMP_01="fail"),
        _row(1, CMP_03="fail"),
        _row(2, CMP_01="fail", CMP_03="fail"),
        _row(3),
        _row(4, status="cand_native_fail"),
    ]
    summary = priors.summarize(rows)
    assert summary["gated"] == 4
    assert summary["cmp01_or_cmp03"]["k"] == 3
    lo, hi = summary["cmp01_or_cmp03"]["ci95"]
    assert lo < 0.75 < hi
    assert summary["per_channel_fail"]["CMP-01"]["k"] == 2


def test_clopper_pearson_edges() -> None:
    assert priors.clopper_pearson(0, 72)[1] == pytest.approx(0.0499, abs=1e-4)
    assert priors.clopper_pearson(5, 5)[1] == 1.0


def test_eval_sensitive_pattern() -> None:
    assert priors.EVAL_SENSITIVE.search("self.bn = nn.BatchNorm2d(16)")
    assert priors.EVAL_SENSITIVE.search("x = F.dropout(x, p=0.1, training=self.training)")
    assert not priors.EVAL_SENSITIVE.search("self.norm = nn.LayerNorm(16)")
