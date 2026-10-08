"""C1 check on the pinned OSWorld b138d348 code (metric image, --network none, no VM).

For real pool tasks whose result getters swallow transport errors, run the pinned
DesktopEnv.evaluate() as the old runner did and LiveTask.evaluate() as the new one does,
against (a) a dead guest port and (b) a guest that answers /terminal and resets every other
connection. time.sleep is skipped (control flow only: the pinned retries sleep 5 s).
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
import requests  # noqa: E402

PICK = ["dfac9ee8", "9bc3cc16", "d38192b0", "7b7617bd", "5ac2891a", "53ad5833", "c59742c0",
        "47f7c0ce", "035f41ba", "0a211154", "0bf05a7d", "185f29bd", "26150609"]


def old_is_transport(exc):
    return isinstance(exc, L.TransportFailure | requests.exceptions.ConnectionError
                      | requests.exceptions.Timeout)


class Half(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        return None

    def do_GET(self):  # noqa: N802
        if self.path == "/terminal":
            body = b'{"output": ""}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.close_connection = True

    def do_POST(self):  # noqa: N802
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self.close_connection = True


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


half = Server(("127.0.0.1", 0), Half)
threading.Thread(target=half.serve_forever, daemon=True).start()
PORTS = {"dead": 5999, "half": half.server_address[1]}


def task_of(prefix):
    paths = glob.glob(f"{OSW}/evaluation_examples/examples/*/{prefix}*.json")
    return json.loads(Path(paths[0]).read_text())


rows = []
for prefix in PICK:
    task = task_of(prefix)
    ev = task["evaluator"]
    res = ev.get("result")
    kinds = [r.get("type") for r in (res if isinstance(res, list) else [res]) if r]
    for mode, port in PORTS.items():
        row = {"task": prefix, "getters": kinds, "postconfig": [s["type"] for s in ev.get("postconfig", [])],
               "mode": mode}
        for which in ("pinned", "live"):
            lt = L.LiveTask(task, osworld_dir=OSW, file_cache=CACHE, guest_ip="127.0.0.1",
                            server_port=port, cache_root=Path(f"/tmp/cache-{mode}-{which}"))
            env = lt.env
            env._set_task_info(task)
            env.setup_controller.reset_cache_dir(env.cache_dir)
            start = len(lt.guest_errors)
            try:
                if which == "pinned":
                    env.action_history = []
                    value = env.evaluate()
                else:
                    value = lt.evaluate(None)
                row[which] = {"returned": repr(value)[:60]}
            except Exception as exc:  # noqa: BLE001
                row[which] = {"raised": type(exc).__name__, "message": str(exc)[:160],
                              "old_rule_transport": old_is_transport(exc),
                              "new_rule_transport": L.is_transport_error(exc)}
            row[which]["guest_request_errors"] = len(lt.guest_errors) - start
            lt.close()
        # What the old runner recorded: transport only if the old rule saw it.
        pinned = row["pinned"]
        row["old_runner"] = ("transport" if pinned.get("old_rule_transport") else
                             "scored (metric_exception, 0)" if "raised" in pinned else
                             f"scored {pinned['returned']}")
        row["new_runner"] = ("transport" if row["live"].get("new_rule_transport") else
                             "scored")
        rows.append(row)
        print(json.dumps(row), flush=True)

summary = {
    "rows": len(rows),
    "old_runner_scored": sum(not r["old_runner"].startswith("transport") for r in rows),
    "new_runner_transport": sum(r["new_runner"] == "transport" for r in rows),
}
print(json.dumps({"summary": summary}))
Path("/out/transport-check.json").write_text(json.dumps({"rows": rows, "summary": summary}, indent=1))
