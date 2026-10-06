from pathlib import Path

from scripts.analyze_memorybank_frozen_controls import analyze_frozen_controls

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_frozen_memorybank_controls_have_registered_contrast() -> None:
    report = analyze_frozen_controls(
        PROJECT_ROOT / "data/results/memorybank-decay/frozen-controls-v1"
    )

    assert report["status"] == "MEMORYBANK_FROZEN_CONTROL_CONTRAST_PASS"
    assert report["candidate_served_on_all_serve_storage_and_service"] == {
        "corrected": 22,
        "no_decay": 200,
        "upstream_precedence": 0,
    }
    assert report["pairwise"]["corrected_vs_upstream_precedence"] == {
        "candidate_service_disagreements": 22,
        "by_stratum": {"active_core": 22},
    }
    assert all(report["gates"].values())
