#!/usr/bin/env python3
"""Write the six preflight doctor records for R01's fresh run under D75 (repair of wave 1).

Same structure as ``../write_doctors.py`` (wave 1, kept): PASS or FAIL, evidence, remediation; the
citation record carries the claim registry parsed from the repaired proposal. Run from the
worktree root after the snapshots exist.

Usage: python3 write_doctors_v2.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
B = ROOT / "program/proposals/evidence/2026-10-11-r01-rerun-noise-sources"
PROPOSAL = ROOT / "program/proposals/2026-10-11-r01-rerun-noise-sources.md"
LEVEL = {
    "F": "full text read with orx paper --full (a wave-1 cell, or the repair owner for C31-C35)",
    "A": "abstract or report only",
    "R": "repository record",
    "1P": "first-party page",
}


def claims() -> list[dict]:
    text = PROPOSAL.read_text(encoding="utf-8")
    sec = text.split("## Primary-Source Evidence", 1)[1].split("\n## ", 1)[0]
    snaps = {
        json.loads(p.read_text())["url"]: json.loads(p.read_text())["http_status"]
        for p in (B / "snapshots").glob("*.json")
    }
    out = []
    for line in sec.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5 or not re.fullmatch(r"[CR]\d+", cells[0]):
            continue
        cid, claim, src, date, lvl = cells
        url = src.strip("`")
        verdict, note = "VERIFIED", None
        if lvl == "A" and "openreview.net" in url:
            verdict, note = (
                "VERIFIED-ABSTRACT",
                "full text UNVERIFIABLE_ACCESS (browser challenge, not bypassed)",
            )
        elif lvl == "A":
            verdict = "VERIFIED-ABSTRACT"
        elif lvl == "1P":
            verdict, note = "FIRST-PARTY", "not replicated"
        if cid == "C03":
            note = (
                "full text UNVERIFIABLE_ACCESS: OpenReview PDF through the host relay and the API attachment route both "
                "returned HTTP 403 browser challenges on 2026-10-11 (not bypassed); abstract only"
            )
        if cid == "C30":
            note = (
                "licence confirmed on 2026-10-11 through https://huggingface.co/api/models/Qwen/Qwen3.5-4B: "
                "cardData.license apache-2.0, sha 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a (S1a's revision)"
            )
        out.append(
            {
                "claim_id": cid,
                "claim": claim,
                "source": url,
                "date": date,
                "read_level": LEVEL.get(lvl, lvl),
                "verdict": verdict,
                "snapshot_http_status": snaps.get(url),
                **({"note": note} if note else {}),
            }
        )
    return out


def main() -> int:
    d = B / "doctors"
    reg = claims()
    power = json.loads((B / "compute/repair-d75/power-r01-v2.json").read_text())
    caps = json.loads((B / "compute/repair-d75/caps-r01-v2.json").read_text())
    q2 = json.loads((B / "query-log-run2.json").read_text())
    val = power["PRED"]["validation"]["4B/H-OSW-fixed"]
    recs = {
        "source": {
            "name": "Source",
            "status": "PASS",
            "run": "D75 repair (fresh run 2)",
            "protocol": "K-Dense literature-review (PRISMA counts)",
            "evidence": [
                f"this run: {q2['counted']['total']} counted orx discover queries with returned ids and raw-output SHA-256 (query-log-run2.json); "
                f"{len(q2['reads_not_counted'])} reads beyond the title",
                "wave 1: 125 counted orx discover queries and 16 OpenReview api2 searches (query-log.json; wave-1 record)",
                "source cutoff 2026-10-11; orx alphaXiv and OpenAlex reachable from the Mac",
            ],
            "degraded_coverage": [
                "orx client outdated (0.2.2 against 0.2.18)",
                "cELldjX2oq full text behind a browser challenge on both reachable routes (not bypassed)",
                "no Semantic Scholar or Google Scholar citers, GitHub code search, vLLM issues, patents, X, Reddit, Chinese-language venues",
                "no OpenReview or ACL Anthology search in this run (wave 1's stand)",
            ],
            "prisma_run2": q2["prisma"],
            "remediation": "Semantic Scholar citer refresh for 2604.17849, cELldjX2oq and 2103.04514 through the host relay when free",
        },
        "citation": {
            "name": "Citation",
            "status": "PASS",
            "protocol": "ARS claim_verification_protocol.md",
            "claim_registry": reg,
            "summary": {
                "claims": len(reg),
                "verified_full_or_repository": sum(c["verdict"] == "VERIFIED" for c in reg),
                "abstract_only": sum(c["verdict"] == "VERIFIED-ABSTRACT" for c in reg),
                "first_party": sum(c["verdict"] == "FIRST-PARTY" for c in reg),
            },
            "remediation": "Read cELldjX2oq in full if a copy becomes reachable; replicate first-party figures before any claim rests on them",
        },
        "novelty": {
            "name": "Novelty",
            "status": "FAIL",
            "evidence": [
                "NARROWED: no direct prior found through 2026-10-11 under the recorded coverage",
                "the adjacent training-nondeterminism field (2103.04514, 1809.05676, 2106.11872) read in full and credited; ledger row 4 rewritten as a setting-plus-measurement delta",
                "identical-input replay literature credited for the serving cells (2609.04748, 2606.15621, 2605.27763, 2607.28495, 2601.06118, 2609.38981)",
                "closest prior by mechanism family, cELldjX2oq, still abstract-only",
                "this run's blind critic and novelty refuter have not run",
            ],
            "remediation": "Blind critic on blind/paragraph-3fe4da7c.txt against paragraph-69e5c3ef.txt (and a second call against paragraph-d8ac91b5.txt); novelty refuter",
        },
        "design": {
            "name": "Design",
            "status": "PASS",
            "self_assessed": True,
            "protocol": "K-Dense experimental-design and statistical-power (vendored)",
            "evidence": [
                "primary estimands at the divergence-onset step: 2^3 factorial (serving x clock region x other regions) on 226 step-1 pairs on 113 tasks; step 2 secondary on 113",
                "controls: replica floor, P0/P0' bitwise self-test, VAL against S1a's 205/226 and 79/226, cross-schedule live comparisons, pixel-checked composites, prompt-id fidelity, positive control",
                "falsifiers P1-P8, P-VAL, P-K6, K1-K6 (registration v2 section 3.2 and 10)",
                "operating characteristics of every rule under the registered estimator: compute/repair-d75/power-r01-v2.json (seeds 42-44)",
                f"two-stage model validated on S1a: largest IR-identity gap {val['max_abs_gap']}, D_w {val['D_w_model']} against {val['D_w_observed']}",
            ],
            "limits": [
                "self-assessed: this run's identification refuter has not run",
                "step 2's earlier reply is prefilled from text, not decoded (2607.28495): step 2 is secondary",
                "the serving factor is S1a's configuration as a bundle (batch, cache hits, Mamba mode); channels secondary",
                "the D_w predictions assume rho and q do not depend on the source that started the onset",
            ],
            "remediation": "Identification refuter; pre-freeze audit",
        },
        "compute": {
            "name": "Compute",
            "status": "FAIL",
            "evidence": [
                "executable CPU pilot: Stage A0 as orx cpu-doctor run 83ee815a-426a-4b94-a93f-cc1277972d76 (exit 0), receipt byte-identical to the committed census",
                "built and CPU-tested against fakes: harness/r01 (regions, requests, replay, p0, openloop, fake_engine, caps, estimators, stepkick) with tests/test_r01_*.py",
                f"registered caps {caps['total_cap_gpu_h']} cap-GPU-h with conditional jobs, {caps['total_cap_gpu_h_without_conditional']} without (compute/repair-d75/caps-r01-v2.json)",
            ],
            "missing": [
                "R01 lane adapter for A1 and Stage C",
                "corpus builder and Stage B report CLIs",
                "manifests",
                "container smoke",
                "Slurm dry run and test-only",
                "P0 on the real engine",
                "the deterministic doctor's real-model-loop and benchmark-adapter attestations",
            ],
            "remediation": "Registration v2 section 16, items 1-6",
        },
        "safety": {
            "name": "Safety",
            "status": "PASS",
            "evidence": [
                "no training, no downloads, no outward action; offline VMs on the certified lane",
                "licences: OSWorld Apache-2.0, Qwen3.5-4B Apache-2.0, vLLM Apache-2.0",
                "screenshots and request bodies stay on the host; repository receives hashes and counts only",
                "host rule: read-only squeue before submissions; no overlap with other workflows' jobs; this run made no host job",
            ],
            "remediation": "none",
        },
    }
    for name, rec in recs.items():
        (d / f"{name}.json").write_text(
            json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(name, rec["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
