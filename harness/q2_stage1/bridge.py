"""The engine bridge under D13 (registration section 3.1 item 4).

The S1a GPU job runs in the research lane's container with ``--network none``; vLLM inside
it listens on 127.0.0.1:8000 only (``plan.engine_argv``). Episode runners sit in each VM
container's ``--network none`` namespace, so neither side can reach the other over TCP and
no Docker network is created. The bridge joins them through the filesystem:

* ``Forwarder`` listens on a Unix-domain socket (mode 0600) in a host directory that the GPU
  container mounts read-write (its ``/outputs``) and each GPU-less runner mounts read-only,
  and copies every connection byte for byte to 127.0.0.1:8000. Connecting to a socket on a
  read-only mount is allowed; creating one is not, so only the engine side can create it.
* ``serve`` (``python -m harness.q2_stage1.bridge serve``) is the GPU job's workload: it
  starts the engine with the registered argv, waits for ``/health``, starts the forwarder,
  writes ``ready.json``, samples GPU memory and utilisation, and stops when the VM job
  writes ``vm.done`` into the bridge directory, or on the lane's USR1 (it writes
  ``usr1.json``, which the VM job polls to stop dispatching, and the lane's checkpoint
  marker with ``trigger=SIGUSR1``) or TERM.

Remaining exposure, recorded with every job: any process of the research account on the
host can connect to the socket while it exists (the host is single-user, D13). Standard
library only.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import signal
import socket
import socketserver
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from typing import Any

SOCKET_NAME = "engine.sock"
READY_NAME = "ready.json"
USR1_NAME = "usr1.json"
DONE_NAME = "vm.done"
FAILED_NAME = "failed.json"
ENGINE_HOST = "127.0.0.1"
ENGINE_PORT = 8000
BUFFER = 1 << 16


def atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _pump(src: socket.socket, dst: socket.socket) -> None:
    try:
        while True:
            data = src.recv(BUFFER)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for sock, how in ((dst, socket.SHUT_WR), (src, socket.SHUT_RD)):
            with contextlib.suppress(OSError):
                sock.shutdown(how)


class _UnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


class Forwarder:
    """Unix-domain socket -> TCP 127.0.0.1:``port``, one thread pair per connection."""

    def __init__(self, socket_path: str, port: int = ENGINE_PORT, host: str = ENGINE_HOST):
        if host != ENGINE_HOST:
            raise ValueError("the bridge forwards to the loopback engine only (D13)")
        self.socket_path = socket_path
        self.port = port
        self.host = host
        self.connections = 0
        self._server: _UnixServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> Forwarder:
        forwarder = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                forwarder.connections += 1
                try:
                    upstream = socket.create_connection((forwarder.host, forwarder.port), 10)
                except OSError:
                    return
                upstream.settimeout(None)
                self.request.settimeout(None)
                back = threading.Thread(target=_pump, args=(upstream, self.request), daemon=True)
                back.start()
                _pump(self.request, upstream)
                back.join()
                upstream.close()

        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        old = os.umask(0o177)
        try:
            self._server = _UnixServer(self.socket_path, Handler)
        finally:
            os.umask(old)
        os.chmod(self.socket_path, 0o600)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)


def engine_healthy(port: int = ENGINE_PORT, timeout: float = 5.0) -> bool:
    try:
        with urllib.request.urlopen(  # noqa: S310 - loopback engine only
            f"http://{ENGINE_HOST}:{port}/health", timeout=timeout
        ) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def gpu_sample() -> list[dict[str, Any]] | None:
    """One nvidia-smi sample per visible GPU; the UUID is replaced by its SHA-256 (section 16)."""
    query = "index,uuid,memory.used,memory.total,utilization.gpu"
    try:
        out = subprocess.run(
            ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=20, check=True,
        ).stdout  # fmt: skip
    except (OSError, subprocess.SubprocessError):
        return None
    rows = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 5:
            continue
        rows.append(
            {
                "index": int(parts[0]) if parts[0].isdigit() else parts[0],
                "uuid_sha256": hashlib.sha256(parts[1].encode()).hexdigest(),
                "memory_used_mib": float(parts[2]) if parts[2] else None,
                "memory_total_mib": float(parts[3]) if parts[3] else None,
                "utilization_pct": float(parts[4]) if parts[4] else None,
            }
        )
    return rows


def write_marker(signal_name: str) -> None:
    """The research lane's checkpoint marker for a signal (``trigger=SIG<name>``)."""
    marker = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
    if not marker:
        return
    path = Path(marker)
    atomic_write(path, f"trigger=SIG{signal_name}\nworkload=q2-stage1-bridge\nt={time.time()}\n")


def serve(
    engine_argv: Sequence[str],
    bridge_dir: Path,
    *,
    port: int = ENGINE_PORT,
    health_timeout_s: float = 900.0,
    gpu_sample_s: float = 30.0,
    poll_s: float = 0.5,
    max_wall_s: float | None = None,
) -> int:
    """Run the engine and the forwarder until ``vm.done``, USR1, TERM or ``max_wall_s``."""
    bridge_dir.mkdir(parents=True, exist_ok=True)
    events: dict[str, float] = {}

    def on_signal(signum: int, _frame: Any) -> None:
        name = signal.Signals(signum).name.removeprefix("SIG")
        events.setdefault(name, time.time())

    signal.signal(signal.SIGUSR1, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    argv = list(engine_argv)
    started = time.time()
    log = (bridge_dir / "engine.log").open("ab")
    engine = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    status: dict[str, Any] = {
        "schema": "q2-stage1a-bridge-v1",
        "engine_argv": argv,
        "engine_argv_sha256": hashlib.sha256(json.dumps(argv).encode()).hexdigest(),
        "engine_pid": engine.pid,
        "socket": SOCKET_NAME,
        "socket_mode": "0600",
        "engine_bind": f"{ENGINE_HOST}:{port}",
        "t_start": started,
        "exposure": "any process of the research account on the host can connect to the "
        "socket while it exists (single-user host, D13)",
    }
    deadline = started + health_timeout_s
    while not engine_healthy(port):
        if engine.poll() is not None or time.time() > deadline or events:
            status.update(t_failed=time.time(), engine_returncode=engine.poll(), events=events)
            atomic_write(bridge_dir / FAILED_NAME, json.dumps(status, indent=2, sort_keys=True))
            _stop_engine(engine)
            log.close()
            return 3
        time.sleep(poll_s)
    forwarder = Forwarder(str(bridge_dir / SOCKET_NAME), port).start()
    status["t_ready"] = time.time()
    atomic_write(bridge_dir / READY_NAME, json.dumps(status, indent=2, sort_keys=True))
    gpu_log = (bridge_dir / "gpu.jsonl").open("a", encoding="utf-8")
    next_sample = 0.0
    reason = "vm_done"
    try:
        while True:
            now = time.time()
            if gpu_sample_s and now >= next_sample:
                gpu_log.write(json.dumps({"t": now, "gpus": gpu_sample()}) + "\n")
                gpu_log.flush()
                next_sample = now + gpu_sample_s
            if (bridge_dir / DONE_NAME).exists():
                reason = "vm_done"
                break
            if "USR1" in events:
                reason = "usr1"
                atomic_write(
                    bridge_dir / USR1_NAME, json.dumps({"t": events["USR1"], "signal": "USR1"})
                )
                write_marker("USR1")
                break
            if "TERM" in events:
                reason = "term"
                atomic_write(
                    bridge_dir / USR1_NAME, json.dumps({"t": events["TERM"], "signal": "TERM"})
                )
                write_marker("TERM")
                break
            if engine.poll() is not None:
                reason = "engine_exited"
                break
            if max_wall_s is not None and now - started > max_wall_s:
                reason = "max_wall"
                break
            time.sleep(poll_s)
    finally:
        forwarder.stop()
        returncode = _stop_engine(engine)
        gpu_log.close()
        log.close()
        status.update(
            t_end=time.time(),
            stop_reason=reason,
            engine_returncode=returncode,
            connections=forwarder.connections,
        )
        atomic_write(bridge_dir / "stopped.json", json.dumps(status, indent=2, sort_keys=True))
    return 0 if reason in ("vm_done", "usr1") else 4


def _stop_engine(engine: subprocess.Popen, grace_s: float = 30.0) -> int | None:
    if engine.poll() is None:
        try:
            os.killpg(engine.pid, signal.SIGTERM)
        except OSError:
            engine.terminate()
        try:
            engine.wait(grace_s)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(engine.pid, signal.SIGKILL)
            except OSError:
                engine.kill()
            engine.wait(10)
    return engine.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("serve", help="run the engine and the forwarder (GPU job workload)")
    run.add_argument("--bridge-dir", type=Path, required=True)
    group = run.add_mutually_exclusive_group(required=True)
    group.add_argument("--size", choices=("4B", "9B", "anchor"), help="registered engine argv")
    group.add_argument("--engine-argv-json", help="explicit argv (tests and dev only)")
    run.add_argument("--health-timeout-s", type=float, default=900.0)
    run.add_argument("--gpu-sample-s", type=float, default=30.0)
    run.add_argument("--max-wall-s", type=float, default=None)
    run.add_argument("--port", type=int, default=ENGINE_PORT, help="tests only; 8000 otherwise")
    fwd = sub.add_parser("forward", help="forward a socket to the loopback engine port")
    fwd.add_argument("--socket", required=True)
    fwd.add_argument("--port", type=int, default=ENGINE_PORT)
    fwd.add_argument("--seconds", type=float, default=None)
    args = parser.parse_args(argv)
    if args.command == "forward":
        forwarder = Forwarder(args.socket, args.port).start()
        try:
            end = None if args.seconds is None else time.time() + args.seconds
            while end is None or time.time() < end:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            forwarder.stop()
        return 0
    if args.size:
        from harness.q2_stage1 import plan

        model_dir = plan.MODEL_DIRS[args.size]
        engine = plan.engine_argv(model_dir, plan.SERVED_NAME, anchor=args.size == "anchor")
        if args.port != ENGINE_PORT:
            raise SystemExit("the registered engine argv binds port 8000")
    else:
        engine = json.loads(args.engine_argv_json)
        if not isinstance(engine, list) or not all(isinstance(a, str) for a in engine):
            raise SystemExit("--engine-argv-json must be a JSON list of strings")
    return serve(
        engine,
        args.bridge_dir,
        port=args.port,
        health_timeout_s=args.health_timeout_s,
        gpu_sample_s=args.gpu_sample_s,
        max_wall_s=args.max_wall_s,
    )


if __name__ == "__main__":
    sys.exit(main())
