"""R01 (`r01-rerun-noise-sources-v2`, DRAFT): where S1a's greedy rerun disagreement starts.

Built and tested on the development Mac's CPU against fakes; nothing here has run a model.

* ``regions``: the clock box (full label extent), region swaps and masks on raw PNGs, the
  pixel-difference census.
* ``requests``: step-1 and step-2 request bodies rebuilt by the frozen H-OSW-fixed client from
  frames and S1a's recorded replies, the 2 x 2 observation composites, prompt-id fidelity.
* ``replay``: the Stage B request-replay driver (batch-1, cold/warm and loaded protocols, cache
  resets, append-only results, the resume rules).
* ``p0``: the P0 bitwise self-test and the per-job timing gate.
* ``openloop``: the Stage A1 capture mode and the Stage C open-loop replay of recorded IR.
* ``fake_engine``: an OpenAI-compatible engine with controllable nondeterminism (tests only).
* ``caps``: per-request prices from S1a's realized step costs and the loaded-pass simulation.
* ``estimators``: the registered cell hazards, task-cluster bootstrap and readings.
* ``stepkick``: the two-stage onset model, its fit on S1a and the removal predictions.
"""
