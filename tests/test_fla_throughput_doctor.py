import json

import pytest

from scripts import fla_throughput_doctor as doctor


def test_plan_matches_registered_shape() -> None:
    plan = doctor.make_plan("gdn-hybrid-125m", seq_len=2048, batch=16, warmup=5, steps=20)
    assert plan.layers == 12 and plan.hidden == 768
    assert 100 < plan.params_millions < 160
    assert plan.flops_per_token > 6 * plan.params_millions * 1e6


def test_dry_run_writes_receipt_without_torch(tmp_path) -> None:
    output = tmp_path / "receipt.json"
    assert doctor.main(["--output", str(output), "--dry-run", "--shape", "gdn-hybrid-350m"]) == 0
    receipt = json.loads(output.read_text())
    assert receipt["dry_run"] is True
    assert receipt["plan"]["shape"] == "gdn-hybrid-350m"
    assert "measurement" not in receipt
    assert receipt["evidence_grade"].startswith("infrastructure-only")


def test_rejects_degenerate_arguments() -> None:
    with pytest.raises(SystemExit):
        doctor.parse_args(["--output", "x.json", "--seq-len", "16"])
