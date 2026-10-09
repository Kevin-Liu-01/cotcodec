"""D53 (iii) check on the pinned OSWorld b138d348 code (metric image, --network none, no VM).

For every dev-split task (no confirm task), run the pinned DesktopEnv.evaluate() as the old
runner did and LiveTask.evaluate() as the new one does, against stand-in guests that answer
like the pinned guest server when a handler fails (HTTP 500, JSON body):

* ``file500``: ``/file`` answers 500; ``/terminal``, ``/setup/*`` and ``/execute`` are healthy;
* ``reads500``: ``/file`` and ``/execute`` answer 500 (the reads a getter makes through
  ``get_file`` and ``execute_python_command``); ``/terminal`` and ``/setup/*`` are healthy;
* ``missing404``: a healthy server on which no file exists (``/file`` answers 404): the
  agent's state, which both rules must score.

time.sleep and the get_file retry pause are skipped (control flow only: the pinned retries
sleep 5 s). No file content is
recorded.
"""
import glob
import http.server
import json
import socketserver
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, "/src")
from harness.q2_stage1 import osworld_live as L  # noqa: E402

OSW = "/inputs/OSWorld"
CACHE = Path("/inputs/file_cache_1e112283/files")
L.import_osworld(OSW)
time.sleep = lambda s: None
# get_file's retry pause reads this module constant through a sleep bound at import time.
L.GET_FILE_INTERVAL_S = 0.0
SPLITS = json.loads(Path("/src/program/evidence/q2-mutation/splits.json").read_text())
ERROR = b'{"status": "error", "message": "handler failed"}'


def handler(mode):
    class Guest(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            return None

        def reply(self, status, body, ctype="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def failing(self, path):
            if mode == "file500":
                return path == "/file"
            if mode == "reads500":
                return path in ("/file", "/execute")
            return False

        def do_GET(self):  # noqa: N802
            path = self.path.split("?")[0]
            if self.failing(path):
                self.reply(500, ERROR)
            elif path == "/terminal":
                self.reply(200, b'{"output": "", "status": "success"}')
            else:
                self.reply(404, b'{"error": "not found"}')

        def do_POST(self):  # noqa: N802
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            path = self.path.split("?")[0]
            if self.failing(path):
                self.reply(500, ERROR)
            elif path == "/file":
                self.reply(404, b'{"error": "File not found"}')
            elif path.startswith("/setup/") or path == "/execute":
                out = {"status": "success", "output": "/home/user/missing\n", "error": "",
                       "returncode": 0}
                self.reply(200, json.dumps(out).encode())
            else:
                self.reply(404, b'{"error": "not found"}')

    return Guest


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


PORTS = {}
for mode in ("file500", "reads500", "missing404"):
    server = Server(("127.0.0.1", 0), handler(mode))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    PORTS[mode] = server.server_address[1]


def task_of(task_id):
    paths = glob.glob(f"{OSW}/evaluation_examples/examples/*/{task_id}.json")
    return json.loads(Path(paths[0]).read_text())


def new_runner(exc):
    """The driver's classification of what LiveTask.evaluate raised (section 7.2)."""
    if exc is None:
        return "scored"
    if L.is_transport_error(exc):
        return "transport"
    if L.is_observation_failure(exc):
        return "guest_observation"
    if L.is_offline_refusal(exc):
        return "offline_network"
    return "scored (metric_exception, 0)"


rows = []
for task_id in sorted(SPLITS["dev"]):
    task = task_of(task_id)
    ev = task["evaluator"]
    res = ev.get("result")
    kinds = [r.get("type") for r in (res if isinstance(res, list) else [res]) if r]
    for mode, port in PORTS.items():
        row = {"task": task_id[:8], "getters": kinds, "mode": mode}
        for which in ("pinned", "live"):
            lt = L.LiveTask(task, osworld_dir=OSW, file_cache=CACHE, guest_ip="127.0.0.1",
                            server_port=port, cache_root=Path(f"/tmp/cache-{mode}-{which}-{task_id}"))
            env = lt.env
            env._set_task_info(task)
            env.setup_controller.reset_cache_dir(env.cache_dir)
            error = None
            try:
                if which == "pinned":
                    env.action_history = []
                    value = env.evaluate()
                else:
                    value = lt.evaluate(None)
                row[which] = {"returned": repr(value)[:40]}
            except Exception as exc:  # noqa: BLE001
                error = exc
                row[which] = {"raised": type(exc).__name__, "message": str(exc)[:160]}
            if which == "live":
                row["new_runner"] = new_runner(error)
                summary = lt.observation_summary()
                row["observations"] = {k: summary[k] for k in ("calls", "retried", "undelivered")}
            else:
                row["old_runner"] = ("scored (metric_exception, 0)" if error is not None
                                     else f"scored {row['pinned']['returned']}")
            lt.close()
        rows.append(row)
        print(json.dumps(row), flush=True)

summary = {
    "rows": len(rows),
    "by_mode": {
        mode: {
            "old_runner_scored": sum(r["old_runner"].startswith("scored") for r in rows
                                     if r["mode"] == mode),
            "new_runner": {k: sum(1 for r in rows if r["mode"] == mode and r["new_runner"] == k)
                           for k in sorted({r["new_runner"] for r in rows})},
        }
        for mode in PORTS
    },
}
print(json.dumps({"summary": summary}))
Path("/out/observation-check.json").write_text(json.dumps({"rows": rows, "summary": summary},
                                                          indent=1))
