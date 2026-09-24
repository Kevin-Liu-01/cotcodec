from __future__ import annotations

from scripts.run_qwen35_recurrent_state_interface_doctor import judge_interface


def passing_metrics() -> dict:
    return {
        "layers": 32,
        "linear_layers": 24,
        "full_attention_layers": 8,
        "linear_states_present": 24,
        "linear_state_shape_exact": True,
        "full_attention_caches_present": 8,
        "all_states_finite": True,
        "prefix_cache_length_exact": True,
        "continuation_cache_length_exact": True,
        "changed_linear_layers": 24,
        "logit_cosine": 0.9995,
        "logit_max_abs": 0.20,
    }


def test_interface_gates_pass_registered_qwen_topology() -> None:
    assert all(judge_interface(passing_metrics()).values())


def test_interface_gates_fail_missing_state_or_cache_parity() -> None:
    metrics = passing_metrics()
    metrics.update(
        {
            "linear_states_present": 23,
            "changed_linear_layers": 22,
            "logit_cosine": 0.998,
            "logit_max_abs": 0.26,
        }
    )
    gates = judge_interface(metrics)
    assert gates["linear_states_present"] is False
    assert gates["continuation_updates_every_linear_layer"] is False
    assert gates["cached_vs_one_shot_cosine"] is False
    assert gates["cached_vs_one_shot_max_abs"] is False


def test_interface_gates_reject_nonfinite_logit_metrics() -> None:
    metrics = passing_metrics()
    metrics["logit_cosine"] = float("nan")
    metrics["logit_max_abs"] = float("inf")
    gates = judge_interface(metrics)
    assert gates["cached_vs_one_shot_cosine"] is False
    assert gates["cached_vs_one_shot_max_abs"] is False
