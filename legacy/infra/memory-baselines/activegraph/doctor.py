#!/usr/bin/env python3
"""Two-phase exact-source Active Graph fork and retention falsifier."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from activegraph import FrozenClock, Graph, Runtime, SQLiteEventStore
from activegraph.store.retention import retire

STATE = Path("/state")
DB = STATE / "activegraph.db"
META = STATE / "run-ids.json"


def _new_runtime() -> Runtime:
    return Runtime(Graph(clock=FrozenClock()), persist_to=str(DB), behaviors=[])


def _claims(runtime: Runtime) -> set[str]:
    return {
        str(obj.data.get("text"))
        for obj in runtime.graph.all_objects()
        if obj.type == "memory"
    }


def _phase_one() -> dict[str, object]:
    STATE.mkdir(parents=True, exist_ok=True)
    parent_canary = os.environ["COTCODEC_PARENT_CANARY"]
    fork_canary = os.environ["COTCODEC_FORK_CANARY"]
    sibling_canary = os.environ["COTCODEC_SIBLING_CANARY"]
    rejected_canary = os.environ["COTCODEC_REJECTED_CANARY"]

    parent = _new_runtime()
    parent.graph.add_object("memory", {"text": parent_canary})
    fork_point = parent.graph.events[-1].id
    fork = parent.fork(at_event=fork_point, label="candidate")
    fork.graph.add_object("memory", {"text": fork_canary})
    nested_point = fork.graph.events[-1].id
    nested = fork.fork(at_event=nested_point, label="nested")
    nested.graph.add_object("memory", {"text": sibling_canary})
    parent.graph.add_object("memory", {"text": "parent-tail"})

    diff = parent.diff(fork)
    parent_fork_divergence = (
        parent_canary in _claims(parent)
        and fork_canary not in _claims(parent)
        and fork_canary in _claims(fork)
        and "parent-tail" not in _claims(fork)
        and bool(diff.parent_only_events)
        and bool(diff.fork_only_events)
    )
    nested_fork_isolated = (
        sibling_canary in _claims(nested)
        and sibling_canary not in _claims(parent)
        and sibling_canary not in _claims(fork)
    )

    rejected = _new_runtime()
    rejected.graph.add_object("memory", {"text": rejected_canary})
    rejected_run_id = rejected.run_id
    rejected.graph.store.close()
    first_retire = retire(str(DB), rejected_run_id)
    second_retire = retire(str(DB), rejected_run_id)
    rejected_store = SQLiteEventStore(str(DB), run_id=rejected_run_id)
    rejected_archive = list(rejected_store.iter_archived())
    rejected_store.close()

    run_ids = {
        "parent": parent.run_id,
        "fork": fork.run_id,
        "nested": nested.run_id,
        "rejected": rejected_run_id,
    }
    META.write_text(json.dumps(run_ids, sort_keys=True), encoding="utf-8")
    for runtime in (parent, fork, nested):
        runtime.graph.store.close()

    return {
        "phase": 1,
        "parent_fork_divergence": parent_fork_divergence,
        "nested_fork_isolated": nested_fork_isolated,
        "rejected_run_moved_to_archive": first_retire > 0,
        "rejected_run_retire_idempotent": second_retire == 0,
        "rejected_archive_contains_canary": any(
            rejected_canary in json.dumps(event.to_dict(), sort_keys=True)
            for event in rejected_archive
        ),
        "native_scoped_purge_absent": not any(
            hasattr(SQLiteEventStore, name)
            for name in ("purge", "purge_run", "delete_run", "erase_run")
        ),
    }


def _phase_two() -> dict[str, object]:
    parent_canary = os.environ["COTCODEC_PARENT_CANARY"]
    fork_canary = os.environ["COTCODEC_FORK_CANARY"]
    sibling_canary = os.environ["COTCODEC_SIBLING_CANARY"]
    rejected_canary = os.environ["COTCODEC_REJECTED_CANARY"]
    run_ids = json.loads(META.read_text(encoding="utf-8"))
    parent = Runtime.load(str(DB), run_id=run_ids["parent"], behaviors=[])
    fork = Runtime.load(str(DB), run_id=run_ids["fork"], behaviors=[])
    nested = Runtime.load(str(DB), run_id=run_ids["nested"], behaviors=[])
    rejected = SQLiteEventStore(str(DB), run_id=run_ids["rejected"])
    archived = list(rejected.iter_archived())
    active = list(rejected.iter_events())

    with sqlite3.connect(DB) as connection:
        rejected_rows = connection.execute(
            "SELECT COUNT(*) FROM events_archive WHERE run_id = ?",
            (run_ids["rejected"],),
        ).fetchone()[0]
        rejected_run_row = connection.execute(
            "SELECT COUNT(*) FROM runs WHERE run_id = ?",
            (run_ids["rejected"],),
        ).fetchone()[0]

    checks = {
        "parent_fork_restart_isolated": (
            parent_canary in _claims(parent)
            and fork_canary not in _claims(parent)
            and fork_canary in _claims(fork)
            and "parent-tail" not in _claims(fork)
        ),
        "nested_fork_restart_isolated": (
            sibling_canary in _claims(nested)
            and sibling_canary not in _claims(parent)
            and sibling_canary not in _claims(fork)
        ),
        "rejected_run_active_log_empty": active == [],
        "rejected_run_archive_survived_restart": (
            rejected_rows == len(archived) and rejected_rows > 0
        ),
        "rejected_run_metadata_survived_restart": rejected_run_row == 1,
        "rejected_run_plaintext_survived_restart": rejected_canary.encode()
        in DB.read_bytes(),
    }
    for runtime in (parent, fork, nested):
        runtime.graph.store.close()
    rejected.close()
    return {"phase": 2, **checks}


def main() -> int:
    phase = int(os.environ["COTCODEC_PHASE"])
    report = _phase_one() if phase == 1 else _phase_two()
    values = [value for key, value in report.items() if key != "phase"]
    if not values or not all(value is True for value in values):
        raise RuntimeError(f"Active Graph falsifier check failed: {report}")
    print("COTCODEC_ACTIVEGRAPH_PHASE=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
