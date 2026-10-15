#!/usr/bin/env python3
"""g2c-precision-layout-v1 (EXPLORATORY): teacher-force both new arms' rollouts through r1 and r4.

Runs inside the research overlay (torch 2.11, transformers 5.15, flash-linear-attention 0.5.2)
on the docker-research lane. Input: the tf-input.json of one model's rollout job (both arms,
fp16 and bf16_b528), hash-bound as the study artifact. The paths are G2b's, from the same code
(``scripts/run_g2b_teacher_force.py`` and the G2 pilot's ``scripts/run_g2_teacher_force.py``):

* ``r1``: HF transformers bf16, one unpacked sequence per forward, SDPA (flash or efficient),
  FLA ``chunk_gated_delta_rule`` (the stock resolution in 5.15; a call counter checks the swap).
  Every rollout.
* ``r4``: the fp32 reference (fp32 weights, TF32 off, memory-efficient SDPA, HF's torch-native
  chunked gated delta rule in fp32). G2b's subset: seed 42 and the first 16 of the 24 prompts,
  both arms.

G2b's packed path (r2) is not run: G2b found it equal to r1 on this stack.

Subcommands: ``plan``, ``selftest`` (CPU, a tiny random Qwen3.5), ``run``.
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import g2_pilot as g2  # noqa: E402
from harness import g2c_precision_layout as gc  # noqa: E402
from scripts import run_g2_teacher_force as base  # noqa: E402
from scripts import run_g2b_teacher_force as tfb  # noqa: E402

PATHS = gc.TF_PATHS
GDN_IMPL = {"r1": "fla_chunk", "r4": "torch_chunk_fp32"}
PRECISION = {"r1": "r1_fla_chunk_bf16", "r4": "r4_torch_fp32"}


def check_input(tf_input: dict[str, Any], model_id: str) -> list[dict[str, Any]]:
    """The model's sequences, with unique ids, from this experiment's arms only."""

    if tf_input.get("experiment_id") != gc.EXPERIMENT_ID:
        raise gc.G2cConfigError("study artifact is not this experiment's tf-input")
    sequences = [s for s in tf_input["sequences"] if s["model_id"] == model_id]
    ids = [s["sequence_id"] for s in sequences]
    if len(set(ids)) != len(ids):
        raise gc.G2cConfigError("duplicate sequence ids in the tf-input")
    arms = {s["arm"] for s in sequences}
    if not arms <= set(gc.ARM_NAMES):
        raise gc.G2cConfigError(f"unknown arms in the tf-input: {sorted(arms)}")
    for s in sequences:
        if not s["completion_ids"] or not s["prompt_ids"]:
            raise gc.G2cConfigError(f"{s['sequence_id']}: empty prompt or completion")
    return sequences


def run_main(args: argparse.Namespace) -> int:
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base.set_cache_env(out)
    import numpy as np
    import torch
    import transformers

    config = gc.load_config()
    stop = base.Stop()
    signal.signal(signal.SIGUSR1, stop.handler)
    signal.signal(signal.SIGTERM, stop.handler)
    stop_at, source = g2.deadline(args.allocation_minutes)
    evidence = Path(args.evidence)
    if g2.sha256_file(evidence) != args.expected_evidence_sha256:
        raise gc.G2cConfigError("study artifact digest differs from --expected-evidence-sha256")
    tf_input = json.loads(evidence.read_text(encoding="utf-8"))
    model_id = args.model
    model_cfg = config["models"][model_id]
    sequences = check_input(tf_input, model_id)
    chunk = int(config["teacher_force"]["lm_head_chunk"])
    progress = out / "progress.jsonl"

    def log(event: str, **fields: Any) -> None:
        record = {"utc": g2.utc_now(), "event": event, **fields}
        with progress.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)

    import fla

    summary: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "claim_level": "exploratory",
        "job": "teacher-force",
        "model": model_id,
        "started_at": g2.utc_now(),
        "deadline_source": source,
        "deadline_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stop_at)),
        "evidence_sha256": args.expected_evidence_sha256,
        "sequences": len(sequences),
        "versions": {
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "transformers": transformers.__version__,
            "fla": getattr(fla, "__version__", "?"),
            "python": sys.version,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "paths": {},
    }
    summary["verification"] = g2.verify_model(model_id, model_cfg["receipt_root"])
    device = "cuda"
    summary["trainer_state_probe"] = tfb.probe_trainer_state(torch)
    log("checks", state=summary["trainer_state_probe"])
    t0 = time.time()
    model = base.load_model(torch, g2.MODEL_ROOT / model_id, model_cfg["hf_class"], device)
    summary["load_s"] = round(time.time() - t0, 1)
    switch = tfb.GdnSwitch()
    summary["gdn"] = switch.describe()
    gdn_layers = sum(
        1 for t in model.config.get_text_config().layer_types if t == "linear_attention"
    )
    summary["gdn_layers"] = gdn_layers
    members = gc.tf_members(config, g2.load_prompts(config), sequences)
    summary["path_members"] = {k: len(v) for k, v in members.items()}
    lengths = [len(s["completion_ids"]) for s in sequences]
    offsets = np.concatenate([[0], np.cumsum(lengths)]).astype(np.int64)
    total = int(offsets[-1])
    arrays: dict[str, Any] = {}
    exit_code = 0

    def put(name: str, index: int, values: Any) -> None:
        arrays.setdefault(name, np.full(total, np.nan, dtype=np.float32))
        arrays[name][offsets[index] : offsets[index + 1]] = values

    for path in PATHS:
        if path == "r4" and next(model.parameters()).dtype != torch.float32:
            model = model.float()
        precision = base.set_precision(torch, PRECISION[path])
        switch.use(GDN_IMPL[path])
        p0 = time.time()
        done = 0
        status = "complete"
        record: dict[str, Any] = {
            "gdn_impl": GDN_IMPL[path],
            "precision": precision,
            "members": len(members[path]),
        }
        try:
            for i in members[path]:
                if stop.event.is_set() or time.time() > stop_at:
                    status = "stopped: " + (stop.reason or "deadline")
                    break
                s = sequences[i]
                ids = s["prompt_ids"] + s["completion_ids"]
                calls0 = switch.calls
                with base.sdpa_context(torch, PRECISION[path]):
                    lp, en = base.score_sequence(
                        torch, model, ids, len(s["prompt_ids"]), chunk, device
                    )
                if switch.calls - calls0 != gdn_layers:
                    raise RuntimeError(
                        f"{path}: GDN swap not effective ({switch.calls - calls0} calls)"
                    )
                put(f"logp_{path}", i, lp)
                put(f"ent_{path}", i, en)
                done += 1
        except Exception as exc:  # noqa: BLE001 - recorded; the other path still runs and saves
            status = f"failed: {type(exc).__name__}"
            record["error"] = repr(exc)[:2000]
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        record.update(
            status=status,
            sequences_scored=done,
            wall_s=round(time.time() - p0, 1),
            param_dtype=str(next(model.parameters()).dtype),
        )
        summary["paths"][path] = record
        log("path-done", model=model_id, path=path, **record)
        if status != "complete":
            exit_code = 3
        g2.write_json(out / "summary.json", summary)
    np.savez_compressed(
        out / f"tf-{model_id}.npz",
        offsets=offsets,
        prompt_len=np.asarray([len(s["prompt_ids"]) for s in sequences], dtype=np.int32),
        token_ids=np.asarray([t for s in sequences for t in s["completion_ids"]], dtype=np.int32),
        **arrays,
    )
    g2.write_json(
        out / f"tf-{model_id}-sequences.json",
        [{k: s[k] for k in ("sequence_id", "arm", "prompt_index", "seed")} for s in sequences],
    )
    summary["finished_at"] = g2.utc_now()
    summary["signal"] = stop.reason
    g2.write_json(out / "summary.json", summary)
    if stop.reason:
        g2.write_checkpoint_marker(
            stop.reason, "g2c teacher-force: finished paths saved; no resume"
        )
    return exit_code


def selftest_main(_args: argparse.Namespace) -> int:
    """CPU, tiny random Qwen3.5 in fp32: the swapped torch-chunk rule is the one called (one call
    per GDN layer), the scorer equals a plain forward, entropies are finite, the input checks
    refuse foreign arms and duplicates, and r4 membership is G2b's subset."""

    import numpy as np
    import torch
    import transformers

    torch.manual_seed(42)
    config = gc.load_config()
    prompts = g2.load_prompts(config)
    report: dict[str, Any] = {"transformers": transformers.__version__, "torch": torch.__version__}
    text = dict(
        vocab_size=512,
        hidden_size=64,
        intermediate_size=128,
        num_hidden_layers=4,
        num_attention_heads=4,
        num_key_value_heads=2,
        head_dim=16,
        linear_num_key_heads=2,
        linear_num_value_heads=4,
        linear_key_head_dim=16,
        linear_value_head_dim=16,
        linear_conv_kernel_dim=4,
        full_attention_interval=4,
        attn_output_gate=True,
        layer_types=["linear_attention"] * 3 + ["full_attention"],
        tie_word_embeddings=True,
    )
    vl_config = transformers.Qwen3_5Config(
        text_config=text,
        vision_config=dict(
            depth=1, hidden_size=32, intermediate_size=64, num_heads=2, out_hidden_size=64
        ),
    )
    vl_config.tie_word_embeddings = True
    model = transformers.Qwen3_5ForConditionalGeneration(vl_config).float().eval()
    switch = tfb.GdnSwitch()
    switch.use("torch_chunk_fp32")
    ids = [int(i) for i in torch.randint(0, 512, (130,))]
    prompt_len = 10
    lp, en = base.score_sequence(torch, model, ids, prompt_len, 32, "cpu")
    report["gdn_calls"] = switch.calls
    with torch.inference_mode():
        logits = model(input_ids=torch.tensor([ids]), use_cache=False).logits[0].float()
        ref = torch.log_softmax(logits, -1)[prompt_len - 1 : -1].gather(
            -1, torch.tensor(ids[prompt_len:])[:, None]
        )[:, 0]
    report["scorer_vs_forward_max_abs"] = float(np.abs(lp - ref.numpy()).max())
    report["entropy_finite"] = bool(np.isfinite(en).all())
    seqs = [
        {
            "sequence_id": gb_id,
            "model_id": "qwen3.5-4b",
            "arm": arm,
            "prompt_index": p,
            "seed": seed,
            "prompt_ids": [1, 2],
            "completion_ids": [3],
        }
        for arm in gc.ARM_NAMES
        for seed in config["seeds"]
        for p in sorted(r["prompt_index"] for r in g2.prompt_subset(prompts, 24))
        for gb_id in [f"qwen3.5-4b/{arm}/p{p:03d}/s{seed}"]
    ]
    tf_input = {"experiment_id": gc.EXPERIMENT_ID, "sequences": seqs}
    checked = check_input(tf_input, "qwen3.5-4b")
    members = gc.tf_members(config, prompts, checked)
    report["members"] = {k: len(v) for k, v in members.items()}
    refusals = 0
    for bad in (
        {"experiment_id": "g2b-state-dtype-v1", "sequences": seqs},
        {"experiment_id": gc.EXPERIMENT_ID, "sequences": seqs + seqs[:1]},
        {"experiment_id": gc.EXPERIMENT_ID, "sequences": [dict(seqs[0], arm="bf16")]},
    ):
        try:
            check_input(bad, "qwen3.5-4b")
        except gc.G2cConfigError:
            refusals += 1
    report["input_refusals"] = refusals
    report["ok"] = bool(
        report["gdn_calls"] == 3
        and report["scorer_vs_forward_max_abs"] < 1e-4
        and report["entropy_finite"]
        and report["members"] == {"r1": 144, "r4": 32}
        and refusals == 3
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    sub.add_parser("selftest")
    run = sub.add_parser("run", allow_abbrev=False)
    run.add_argument("--evidence", required=True)
    run.add_argument("--expected-evidence-sha256", required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--allocation-minutes", type=float, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        config = gc.load_config()
        prompts = g2.load_prompts(config)
        print(
            json.dumps(
                {
                    "experiment_id": config["experiment_id"],
                    "paths": PATHS,
                    "gdn_impl": GDN_IMPL,
                    "teacher_force": config["teacher_force"],
                    "r4_prompts": sorted(gc.r4_prompt_indices(config, prompts)),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "selftest":
        return selftest_main(args)
    return run_main(args)


if __name__ == "__main__":
    sys.exit(main())
