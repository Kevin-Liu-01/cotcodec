# Freeze simulation (scratch clone only; the real ledger untouched)

Final simulation, 2026-10-08, on a fresh clone of `stage0/q3-dense-v2` at
`f2510dd` (main merged in at `30f9c7c`, so the clone's ledger is main's, 11
rows ending at `q2-evaluator-mutation-v1`, hash `dc39bfa2...`; the real
ledger file, SHA-256 `1052d58b...`, was not written).

1. The registration's status paragraph rewritten to the frozen wording
   (simulation text: "decisions 16-21 and the limits accepted by the program
   owner ... FREEZE SIMULATION ONLY"). The real freeze names the decision
   that accepts them.
2. `scripts/preregister.py freeze q3-dense-headroom-precheck-v2
   program/preregistrations/q3-dense-headroom-precheck-v2.md`: exit 0; row in
   `scratch-ledger-row.json` (`previous_hash` `dc39bfa2...`, registration
   SHA-256 `2718e81c...` with the simulated status text).
3. `verify`: exit 0. `check-chain`: `{"rows": 12, "status": "PASS"}`.
4. Simulated freeze commit `6e0d841`; in frozen mode
   `tests/test_dense_headroom_v2_prereg.py`, `tests/test_dense_headroom_prereg.py`,
   `tests/test_dense_headroom_v2_manifests.py` and `tests/test_preregister.py`:
   25 passed. The full suite in the frozen clone (macOS) is in
   `pytest-frozen-clone.txt`.
5. The entry point's start-up code-table check against the frozen file: no
   differing file.
6. Filler, 0.6B lane, with a stand-in image receipt (image id all `f`, the
   simulated commit, its `git archive` digest): exit 0
   (`sim-fill-0p6b.json`); the filled manifest differs from the template only
   in the three image FILL values and the preregistration digest.
7. Filler, 4B lane, without `--small-lane-receipt`: exit 2, refused
   (`sim-fill-4b-refused.txt`).
8. `scripts/submit_docker_research_job.py --dry-run` on the filled 0.6B
   manifest: exit 0, 0.2 GPU-h (`sim-dry-run-0p6b.json`; the clone's path
   replaced by `SCRATCH_CLONE`).

`freeze-simulation-de999f7.txt` is the earlier simulation at `de999f7`,
before main was merged (ledger of 7 rows then, `check-chain` 8 rows PASS).
