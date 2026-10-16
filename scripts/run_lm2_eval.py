#!/usr/bin/env python3
"""LM2 (D129, EXPLORATORY) driver: serve one arm with stock llama.cpp and run the task requests.

Runs inside the program's lane, in the overlay of the pinned llama.cpp b11669 CUDA image, on the
GPUs Slurm allocated. For one arm of the committed plan it:

1. refuses to run if physical GPU 0's UUID (another project's) is visible;
2. checks the arm's model receipt (digest, revision, artifact root, file sizes; the full re-hash
   runs in a CPU job), the evaluation files' SHA-256 and the pinned chat template's SHA-256;
3. starts ``llama-server`` with every layer on the GPUs (layer split, ``-fit off``), the arm's
   slot count and per-slot context, and waits for ``/health``;
4. records ``/props`` and renders a fixed probe conversation through ``/apply-template`` with the
   arm's template arguments (a hash and the generation prefix, no benchmark text);
5. sends the requests in the plan's order (item-major, tasks alternating, the seeds of an item
   adjacent), skipping every key already in a ``responses*.jsonl`` under the output directory or a
   ``--prior-dir``; one worker thread per slot;
6. samples ``/metrics``, ``/slots`` and ``nvidia-smi`` throughout (text-free throughput rows);
7. stops dispatching before its time budget, aborts what is still running at the end, and writes a
   text-free summary.

Raw responses (model text) stay in the run directory on the host. Nothing here executes model
output.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.lm2_resident_eval import (  # noqa: E402
    LM2Error,
    chat_payload,
    load_items,
    load_plan,
    max_tokens,
    request_key,
    request_order,
    select_items,
    sha256_bytes,
    sha256_file,
    short_hash,
)
from scripts.fetch_open_model import DEFAULT_REGISTRY, load_registry  # noqa: E402
from scripts.run_lm1_smoke import (  # noqa: E402
    GpuPoller,
    SmokeError,
    check_receipt,
    http_json,
    nvidia_smi_query,
    stop_process,
    summarize_server_log,
)

FIXED_SERVER_ARGS = ("-ngl", "all", "--split-mode", "layer", "-fit", "off")
PROBE_MESSAGES = [{"role": "user", "content": "What is 2 + 3? Reply with one number."}]
RESPONSE_FIELDS = ("finish_reason",)


class Stop(Exception):
    """The time budget or a signal ended dispatching."""


def server_argv(
    plan: dict[str, Any], arm_id: str, gguf: Path, port: int, threads: int, verbosity: int = 3
) -> list[str]:
    arm = plan["arms"][arm_id]
    ctx = arm["slots"] * arm["ctx_per_slot"]
    argv = [
        plan["llama_server"],
        "-m",
        str(gguf),
        *FIXED_SERVER_ARGS,
        "-c",
        str(ctx),
        "-np",
        str(arm["slots"]),
        "--jinja",
        "--metrics",
        "--no-webui",
        "-cram",
        "0",
        "-lv",
        str(verbosity),
        *arm.get("server_args", []),
    ]
    if arm.get("chat_template_file"):
        argv += ["--chat-template-file", str(PROJECT_ROOT / arm["chat_template_file"])]
    argv += ["--host", "127.0.0.1", "--port", str(port), "-t", str(threads)]
    return argv


def parse_metrics(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("llamacpp:"):
            try:
                out[parts[0].split(":", 1)[1]] = float(parts[1])
            except ValueError:
                continue
    return out


def slots_snapshot(body: Any) -> dict[str, Any]:
    """Busy slots and tokens decoded so far by the requests still running (text-free)."""

    busy, decoded = 0, 0
    if isinstance(body, list):
        for slot in body:
            if not isinstance(slot, dict) or not slot.get("is_processing"):
                continue
            busy += 1
            nxt = slot.get("next_token")
            if isinstance(nxt, list):
                nxt = nxt[0] if nxt else {}
            if isinstance(nxt, dict):
                decoded += int(nxt.get("n_decoded", 0) or 0)
    return {"busy_slots": busy, "inflight_decoded": decoded}


def get_text(url: str, timeout: float) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def completed_keys(paths: list[Path]) -> dict[str, dict[str, Any]]:
    done: dict[str, dict[str, Any]] = {}
    for path in paths:
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue  # a line cut by a kill; the key is simply re-run
                if row.get("status") == "ok":
                    done[row["key"]] = {"job": row.get("job_id"), "source": str(path)}
    return done


class Runner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.started = time.monotonic()
        budget = args.allocation_minutes * 60 - args.reserve_s
        self.abort_at = self.started + budget
        self.dispatch_until = self.abort_at - args.drain_s
        self.stopping = threading.Event()
        self.lock = threading.Lock()
        self.state: dict[str, Any] = {"process": None}
        self.counts = {"ok": 0, "http_error": 0, "aborted": 0, "error": 0}
        self.tokens_done = 0

    # -- setup ------------------------------------------------------------------------------
    def setup(self) -> None:
        args = self.args
        self.plan = load_plan(args.plan, args.expected_plan_sha256)
        if args.arm not in self.plan["arms"]:
            raise LM2Error(f"unknown arm {args.arm}")
        if [int(s) for s in args.seeds] != [s for s in self.plan["seeds"] if s in args.seeds]:
            raise LM2Error("--seeds must be a subset of the plan's seeds, in plan order")
        self.arm = self.plan["arms"][args.arm]
        # Slot overrides from the manifest (sized from the pilot); recorded in the summary.
        if args.slots is not None:
            self.arm["slots"] = args.slots
        if args.ctx_per_slot is not None:
            self.arm["ctx_per_slot"] = args.ctx_per_slot
        longest = max(max_tokens(self.plan, args.arm, task) for task in self.plan["tasks"])
        if not 1 <= self.arm["slots"] <= 128 or self.arm["ctx_per_slot"] < longest + 1024:
            raise LM2Error("slot override out of range or context below max_tokens + 1,024")
        self.out = args.output_dir
        self.out.mkdir(parents=True, exist_ok=True)
        self.job_id = os.environ.get("SLURM_JOB_ID") or os.environ.get("COTCODEC_JOB_ID", "local")
        root = Path(self.plan["datasets"]["root"])
        self.items: dict[str, list[dict[str, Any]]] = {}
        for task in self.plan["order"]["interleave"]:
            entry = self.plan["datasets"][task]
            rows = load_items(root / entry["file"], entry["sha256"])
            self.items[task] = select_items(task, self.plan["tasks"][task], rows)
        caps = {}
        for spec in args.cap or []:
            task, _, value = spec.partition("=")
            caps[task] = int(value)
        self.caps = caps
        self.order = request_order(
            self.items,
            self.plan["order"]["interleave"],
            args.seeds,
            self.plan["order"]["rng_seed"],
            caps,
        )
        if self.arm.get("chat_template_file"):
            got = sha256_file(PROJECT_ROOT / self.arm["chat_template_file"])
            if got != self.arm["chat_template_sha256"]:
                raise LM2Error("chat template SHA-256 differs from the plan")

    # -- server ------------------------------------------------------------------------------
    def start_server(self, poller: GpuPoller) -> dict[str, Any]:
        args = self.args
        registry = load_registry(DEFAULT_REGISTRY)
        entry = registry["models"][self.arm["model_id"]]
        model = {
            "model_id": self.arm["model_id"],
            "receipt_sha256": self.arm["receipt_sha256"],
            "artifact_root_sha256": self.arm["artifact_root_sha256"],
        }
        info: dict[str, Any] = {
            "receipt": check_receipt(model, entry, args.model_root, args.receipt_root)
        }
        gguf = args.model_root / self.arm["model_id"] / self.arm["gguf"]
        threads = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else 16
        argv = server_argv(self.plan, args.arm, gguf, args.port, threads, args.server_log_verbosity)
        info["server_argv"] = [
            a if a != str(gguf) else f"<snapshot>/{self.arm['gguf']}" for a in argv
        ]
        baseline = poller.reset()
        info["gpus"] = [
            {"uuid": u, "index": r["index"], "total_mib": r["total_mib"]}
            for u, r in sorted(baseline.items(), key=lambda kv: kv[1]["index"])
        ]
        self.log_path = self.out / f"server-{self.job_id}.log"
        log = self.log_path.open("wb")
        started = time.monotonic()
        process = subprocess.Popen(
            argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
        )
        self.state["process"] = process
        base = f"http://127.0.0.1:{args.port}"
        ready = False
        while time.monotonic() - started < self.arm.get("load_timeout_s", 600):
            if process.poll() is not None:
                break
            try:
                status, body = http_json(f"{base}/health", None, 5)
                if status == 200 and isinstance(body, dict) and body.get("status") == "ok":
                    ready = True
                    break
            except (urllib.error.URLError, OSError, json.JSONDecodeError):
                pass
            time.sleep(0.5)
        info["load_s"] = round(time.monotonic() - started, 2)
        peaks, _ = poller.snapshot()
        info["peak_mib_after_load"] = peaks
        if not ready:
            raise LM2Error(f"server not ready after {info['load_s']} s (exit {process.poll()})")
        status, props = http_json(f"{base}/props", None, 30)
        if status == 200 and isinstance(props, dict):
            template = props.get("chat_template") or ""
            info["props"] = {
                "total_slots": props.get("total_slots"),
                "n_ctx": (props.get("default_generation_settings") or {}).get("n_ctx"),
                "chat_template_sha256": sha256_bytes(template.encode("utf-8")),
                "build_info": props.get("build_info"),
                "model_path_tail": str(props.get("model_path", ""))[-60:],
            }
        probe: dict[str, Any] = {"messages": PROBE_MESSAGES}
        if self.arm.get("chat_template_kwargs"):
            probe["chat_template_kwargs"] = self.arm["chat_template_kwargs"]
        if self.arm.get("reasoning_effort"):
            probe["reasoning_effort"] = self.arm["reasoning_effort"]
        status, rendered = http_json(f"{base}/apply-template", probe, 30)
        prompt = rendered.get("prompt", "") if isinstance(rendered, dict) else ""
        info["probe_render"] = {
            "http_status": status,
            "sha256": sha256_bytes(prompt.encode("utf-8")),
            "chars": len(prompt),
            # The generation prefix after the probe's user text (template tokens only).
            "tail_after_user": prompt.split(PROBE_MESSAGES[0]["content"], 1)[-1][-80:],
        }
        self.base = base
        return info

    # -- requests ----------------------------------------------------------------------------
    def worker(self, tasks: queue.Queue, results: Path, wid: int) -> None:
        timeout = self.args.request_timeout_s
        while not self.stopping.is_set():
            try:
                job = tasks.get_nowait()
            except queue.Empty:
                return
            if time.monotonic() > self.dispatch_until:
                self.stopping.set()
                return
            task, item, rank, seed = job
            key = request_key(self.args.arm, task, item["id"], seed)
            payload = chat_payload(self.plan, self.args.arm, task, item, seed)
            t0 = time.monotonic()
            row: dict[str, Any] = {
                "key": key,
                "arm": self.args.arm,
                "task": task,
                "item_id": item["id"],
                "source": item.get("source"),
                "rank": rank,
                "seed": seed,
                "request_seed": payload["seed"],
                "job_id": self.job_id,
                "worker": wid,
                "payload_sha256": short_hash(json.dumps(payload, sort_keys=True)),
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            remaining = self.abort_at - time.monotonic()
            try:
                status, body = http_json(
                    f"{self.base}/v1/chat/completions", payload, max(5.0, min(timeout, remaining))
                )
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                with self.lock:
                    kind = (
                        "aborted"
                        if self.stopping.is_set() or time.monotonic() >= self.abort_at - 1
                        else "error"
                    )
                    self.counts[kind] += 1
                if kind == "error":
                    row.update(
                        status="error",
                        error=f"{type(exc).__name__}",
                        wall_s=round(time.monotonic() - t0, 2),
                    )
                    self._append(results, row)
                continue
            row["wall_s"] = round(time.monotonic() - t0, 2)
            row["http_status"] = status
            if status == 200 and isinstance(body, dict) and body.get("choices"):
                choice = body["choices"][0]
                message = choice.get("message") or {}
                usage = body.get("usage") or {}
                timings = body.get("timings") or {}
                row.update(
                    status="ok",
                    finish_reason=choice.get("finish_reason"),
                    content=message.get("content") or "",
                    reasoning_content=message.get("reasoning_content") or "",
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    timings={
                        k: timings.get(k)
                        for k in ("prompt_n", "prompt_ms", "predicted_n", "predicted_ms")
                    },
                )
                with self.lock:
                    self.counts["ok"] += 1
                    self.tokens_done += int(usage.get("completion_tokens") or 0)
            else:
                row.update(
                    status="http_error",
                    error_sha256_16=short_hash(json.dumps(body, sort_keys=True)),
                )
                with self.lock:
                    self.counts["http_error"] += 1
            self._append(results, row)

    def _append(self, path: Path, row: dict[str, Any]) -> None:
        line = json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n"
        with self.lock, path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())

    def monitor(self, poller: GpuPoller, metrics_path: Path) -> None:
        while not self.stopping.wait(self.args.metrics_interval_s):
            self.sample_metrics(poller, metrics_path)

    def sample_metrics(self, poller: GpuPoller, metrics_path: Path) -> None:
        row: dict[str, Any] = {"t": round(time.monotonic() - self.started, 1)}
        try:
            row["metrics"] = parse_metrics(get_text(f"{self.base}/metrics", 10))
        except (urllib.error.URLError, OSError):
            row["metrics_error"] = True
        try:
            status, body = http_json(f"{self.base}/slots", None, 10)
            if status == 200:
                row.update(slots_snapshot(body))
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            row["slots_error"] = True
        with self.lock:
            row["completed_ok"] = self.counts["ok"]
            row["completed_tokens"] = self.tokens_done
        latest = poller.latest
        row["gpu_used_mib"] = {str(r["index"]): r["used_mib"] for r in latest.values()}
        with metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    def run(self) -> int:
        args = self.args
        self.setup()
        poller = GpuPoller(nvidia_smi_query)
        poller.sample()
        visible = sorted(poller.latest)
        refused = sorted(set(visible) & set(self.plan.get("refuse_gpu_uuids", [])))
        summary: dict[str, Any] = {
            "schema_version": 1,
            "experiment": self.plan["experiment"],
            "arm": args.arm,
            "phase": args.phase,
            "job_id": self.job_id,
            "seeds": args.seeds,
            "caps": self.caps,
            "plan_sha256": sha256_file(args.plan),
            "visible_gpus": len(visible),
            "slots": self.arm["slots"],
            "ctx_per_slot": self.arm["ctx_per_slot"],
        }
        summary_path = self.out / f"summary-{self.job_id}.json"
        if not visible or refused:
            summary.update(refused=True, refused_gpus=refused)
            summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
            print(f"refusing to run: visible {visible}, refused {refused}", file=sys.stderr)
            return 3
        poller.start()

        def on_signal(signum: int, _frame: Any) -> None:
            self.stopping.set()
            self.abort_at = min(self.abort_at, time.monotonic() + 5)

        for sig in (signal.SIGTERM, signal.SIGUSR1, signal.SIGINT):
            signal.signal(sig, on_signal)
        prior = sorted(self.out.glob("responses*.jsonl"))
        for directory in args.prior_dir or []:
            prior += sorted(Path(directory).glob("responses*.jsonl"))
        done = completed_keys(prior)
        todo = [
            job
            for job in self.order
            if request_key(args.arm, job[0], job[1]["id"], job[3]) not in done
        ]
        summary.update(
            order_len=len(self.order), already_done=len(self.order) - len(todo), todo=len(todo)
        )
        results = self.out / f"responses-{self.job_id}.jsonl"
        metrics_path = self.out / f"metrics-{self.job_id}.jsonl"
        exit_code = 1
        try:
            summary["server"] = self.start_server(poller)
            gen_started = time.monotonic()
            summary["generation_started_s"] = round(gen_started - self.started, 1)
            tasks: queue.Queue = queue.Queue()
            for job in todo:
                tasks.put(job)
            mon = threading.Thread(target=self.monitor, args=(poller, metrics_path), daemon=True)
            mon.start()
            workers = [
                threading.Thread(target=self.worker, args=(tasks, results, w), daemon=True)
                for w in range(self.arm["slots"])
            ]
            for w in workers:
                w.start()
            while any(w.is_alive() for w in workers):
                if time.monotonic() >= self.abort_at:
                    self.stopping.set()
                    break
                time.sleep(1.0)
            self.sample_metrics(poller, metrics_path)
            summary["generation_s"] = round(time.monotonic() - gen_started, 1)
            summary["remaining_in_queue"] = tasks.qsize()
            exit_code = 0 if tasks.qsize() == 0 and not self.stopping.is_set() else 4
        finally:
            self.stopping.set()
            process = self.state.get("process")
            if process is not None:
                summary["server_exit_code"] = stop_process(process, grace_s=20)
            poller.stop()
            peaks, samples = poller.snapshot()
            summary["peak_mib"] = peaks
            summary["vram_samples"] = samples
            summary["counts"] = dict(self.counts)
            summary["completed_tokens"] = self.tokens_done
            summary["elapsed_s"] = round(time.monotonic() - self.started, 1)
            if hasattr(self, "log_path") and self.log_path.exists():
                text = self.log_path.read_text(encoding="utf-8", errors="replace")
                summary["server_log"] = {
                    "sha256": sha256_file(self.log_path),
                    **summarize_server_log(text),
                }
                summary["server_log"]["kv_lines"] = [
                    line.strip()[:200]
                    for line in text.splitlines()
                    if "KV" in line and ("MiB" in line or "size" in line)
                ][:40]
            summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(
            json.dumps({k: summary.get(k) for k in ("arm", "counts", "todo", "generation_s")}),
            flush=True,
        )
        return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--expected-plan-sha256")
    p.add_argument("--arm", required=True)
    p.add_argument("--phase", choices=("pilot", "main"), required=True)
    p.add_argument("--seeds", type=int, nargs="+", required=True)
    p.add_argument("--cap", action="append", help="task=N: keep the first N items of a task")
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--prior-dir", action="append", help="read-only dir with earlier responses")
    p.add_argument("--allocation-minutes", type=float, required=True)
    p.add_argument("--reserve-s", type=float, default=200.0)
    p.add_argument("--drain-s", type=float, default=0.0)
    p.add_argument("--request-timeout-s", type=float, default=7200.0)
    p.add_argument("--metrics-interval-s", type=float, default=10.0)
    p.add_argument("--model-root", type=Path, default=Path("/model-cache/cotcodec-models"))
    p.add_argument("--receipt-root", type=Path, default=Path("/model-cache/cotcodec-receipts"))
    p.add_argument("--port", type=int, default=18941)
    p.add_argument("--slots", type=int)
    p.add_argument("--server-log-verbosity", type=int, choices=(3, 4), default=4)
    p.add_argument("--ctx-per-slot", type=int)
    c = sub.add_parser("check-plan")
    c.add_argument("--plan", type=Path, required=True)
    c.add_argument("--expected-plan-sha256")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "check-plan":
        plan = load_plan(args.plan, args.expected_plan_sha256)
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "arms": sorted(plan["arms"]),
                    "plan_sha256": sha256_file(args.plan),
                }
            )
        )
        return 0
    return Runner(args).run()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (LM2Error, SmokeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
