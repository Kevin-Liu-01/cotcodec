"""The operator command line: catalog, plan, manifest, apply-text, verify."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from harness.q2_mutation.operators import _synth as synth
from scripts import q2_mutation_operators as cli


def _spec_file(tmp_path: Path, kind: str) -> Path:
    path = tmp_path / f"{kind}.yaml"
    path.write_text(yaml.safe_dump(synth.synthetic_spec(kind)), encoding="utf-8")
    return path


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_catalog_refuses_overwrite(tmp_path: Path) -> None:
    out = tmp_path / "catalog.json"
    assert cli.main(["catalog", "--out", str(out)]) == 0
    assert json.loads(out.read_text())["total"] >= 40
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        cli.main(["catalog", "--out", str(out)])


def test_config_round_trip_through_the_cli(tmp_path: Path) -> None:
    base = synth.build_json(tmp_path / "settings.json")
    initial = synth.build_json(tmp_path / "init" / "settings.json",
                               {**synth.SETTINGS_JSON, "editor.fontSize": 12})
    plans = tmp_path / "plans.jsonl"
    assert cli.main(["plan", "--spec", str(_spec_file(tmp_path, "config")), "--base", str(base),
                     "--initial", str(initial), "--out", str(plans)]) == 0
    log = tmp_path / "apply.jsonl"
    assert cli.main(["apply-text", "--plans", str(plans), "--base", str(base),
                     "--out-dir", str(tmp_path / "mutants"), "--log", str(log)]) == 0
    results = tmp_path / "results.jsonl"
    assert cli.main(["verify", "--plans", str(plans), "--reference", str(base),
                     "--mutants-dir", str(tmp_path / "mutants"), "--apply-log", str(log),
                     "--out", str(results)]) == 0
    done = _rows(results)
    assert done and all(all(c["passed"] for c in r["purity_checks"]) for r in done)


def test_office_manifest_includes_null_mutant(tmp_path: Path) -> None:
    base = synth.build_xlsx(tmp_path / "saved" / "base" / "w.xlsx")
    plans = tmp_path / "plans.jsonl"
    assert cli.main(["plan", "--spec", str(_spec_file(tmp_path, "xlsx")), "--base", str(base),
                     "--out", str(plans), "--operator", "xlsx.viol.value_perturb"]) == 0
    manifest = tmp_path / "apply.jsonl"
    assert cli.main(["manifest", "--plans", str(plans), "--input-rel", "saved/base/w.xlsx",
                     "--null-rel", "saved/null/w.xlsx", "--out", str(manifest)]) == 0
    rows = _rows(manifest)
    assert rows[0]["steps"] == [] and rows[0]["output"] == "saved/null/w.xlsx"
    assert all(r["output"].startswith("mutants/") for r in rows[1:])
    assert {r["family"] for r in rows} == {"xlsx"}
