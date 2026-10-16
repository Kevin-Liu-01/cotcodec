#!/usr/bin/env python3
"""Text-free per-task summary of a llama-server log: task id, slot, prompt tokens, last n_gen,
whether the task was cancelled and whether it was released normally."""
import json, re, sys
pat_launch = re.compile(r"id +(\d+) \| task (\d+) \| new prompt, n_ctx_slot = \d+, n_keep = \d+, task\.n_tokens = (\d+)")
pat_gen = re.compile(r"\| task (\d+) \| n_gen = +(\d+),")
pat_cancel = re.compile(r"cancel task, id_task = (\d+)")
pat_release = re.compile(r"\| task (\d+) \| stop processing: n_tokens = (\d+), truncated = (\d)")
tasks = {}
with open(sys.argv[1], "rb") as fh:
    for raw in fh:
        line = raw.decode("utf-8", "replace")
        m = pat_launch.search(line)
        if m:
            tasks[int(m.group(2))] = {"task": int(m.group(2)), "slot": int(m.group(1)), "prompt_tokens": int(m.group(3)), "n_gen": 0, "cancelled": False, "released": False}
            continue
        m = pat_gen.search(line)
        if m and int(m.group(1)) in tasks:
            tasks[int(m.group(1))]["n_gen"] = max(tasks[int(m.group(1))]["n_gen"], int(m.group(2)))
            continue
        m = pat_cancel.search(line)
        if m and int(m.group(1)) in tasks:
            tasks[int(m.group(1))]["cancelled"] = True
            continue
        m = pat_release.search(line)
        if m and int(m.group(1)) in tasks:
            tasks[int(m.group(1))]["released"] = True
            tasks[int(m.group(1))]["final_n_tokens"] = int(m.group(2))
for t in sorted(tasks):
    print(json.dumps(tasks[t]))
