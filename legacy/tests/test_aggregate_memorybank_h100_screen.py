from __future__ import annotations

import pytest

from scripts.aggregate_memorybank_h100_screen import _cluster_bootstrap_ratio, _contrast


def test_cluster_bootstrap_ratio_preserves_task_clusters() -> None:
    report = _cluster_bootstrap_ratio(
        {
            "task-a": (2.0, 2),
            "task-b": (-1.0, 1),
            "task-c": (0.0, 3),
        },
        draws=2_000,
        seed=42,
    )
    assert report["point_delta_points"] == pytest.approx(100.0 / 6.0)
    assert report["cluster_count"] == 3
    assert report["observation_count"] == 6
    assert report["ci95_low_points"] <= report["point_delta_points"]
    assert report["ci95_high_points"] >= report["point_delta_points"]


def test_cluster_bootstrap_ratio_rejects_empty_estimand() -> None:
    with pytest.raises(ValueError, match="no observations"):
        _cluster_bootstrap_ratio({"task-a": (0.0, 0)}, draws=10)


def test_contrast_requires_identical_assignments() -> None:
    def cell(visibility: str) -> dict:
        return {
            "metrics": {
                "assignment_schedule_sha256": "schedule",
                "trial_plan_sha256": "plan",
                "task_results": [
                    {
                        "trial_id": "task-a",
                        "group_id": "group-a",
                        "visibility": visibility,
                        "success": True,
                    }
                ],
            }
        }

    cells = {"left": {42: cell("serve")}, "right": {42: cell("holdout")}}
    with pytest.raises(ValueError, match="paired task identity differs"):
        _contrast(left="left", right="right", cells=cells, seeds=(42,))
