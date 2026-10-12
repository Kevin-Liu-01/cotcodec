"""Q2 successor E (`q2-stage1-successor-e-v1`): S1a's design with more data (D66, D69, D80).

All 113 eligible pool tasks, Qwen3.5-4B and 9B, four new serving sessions per size, one
episode per (size, task, harness, session). The episode path (driver, harness clients,
engine bridge, OSWorld checker path, executor) and the estimators and rules are S1a's code
of record (`harness/q2_stage1/`), imported unchanged; this package holds only what E's
design adds: its plan and job order, its record labels, a thin lane over S1a's lane, an
episode entry point and the analysis of a four-session, one-rerun array.
"""
