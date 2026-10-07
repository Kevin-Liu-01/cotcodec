"""Reset sentinel (runs inside the OSWorld guest).

``write <token>`` stores the token in three places a warm reset would keep:
a file in the user's home, a dconf key, and a gsettings key with a schema.
``check`` reads all three back in a fresh process. A cold reset is pristine
when none of them carries a token written by an earlier cycle.
Prints one JSON object.
"""

import json
import os
import subprocess
import sys

FILE = os.path.expanduser("~/.cotcodec_q2ap_sentinel")
DCONF_KEY = "/org/cotcodec/q2ap/sentinel"
GSETTINGS = ["org.gnome.desktop.interface", "cursor-blink-timeout"]
SENTINEL_BLINK = 1777  # far from the schema default (10)


def run(argv):
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=15)
        return done.returncode, done.stdout.strip(), done.stderr.strip()[-300:]
    except Exception as exc:  # noqa: BLE001
        return None, "", repr(exc)[:300]


def check():
    state = {"file": None, "dconf": None, "gsettings": None}
    if os.path.exists(FILE):
        with open(FILE, encoding="utf-8") as handle:
            state["file"] = handle.read().strip()
    rc, out, err = run(["dconf", "read", DCONF_KEY])
    state["dconf"] = out if rc == 0 else f"ERR rc={rc} {err}"
    rc, out, err = run(["gsettings", "get", *GSETTINGS])
    state["gsettings"] = out if rc == 0 else f"ERR rc={rc} {err}"
    return state


def write(token):
    with open(FILE, "w", encoding="utf-8") as handle:
        handle.write(token + "\n")
    results = {
        "dconf": run(["dconf", "write", DCONF_KEY, "'" + token + "'"]),
        "gsettings": run(["gsettings", "set", *GSETTINGS, str(SENTINEL_BLINK)]),
    }
    os.sync()
    return {key: {"rc": value[0], "err": value[2]} for key, value in results.items()}


mode = sys.argv[1]
if mode == "check":
    print(json.dumps({"mode": "check", "state": check()}, sort_keys=True))
elif mode == "write":
    token = sys.argv[2]
    if not token.replace("-", "").isalnum() or len(token) > 80:
        raise SystemExit("unsafe token")
    print(json.dumps({"mode": "write", "token": token, "results": write(token)}, sort_keys=True))
else:
    raise SystemExit("mode must be check or write")
