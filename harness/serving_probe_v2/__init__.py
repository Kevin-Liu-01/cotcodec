"""vLLM serving-throughput probe v2 (experiment serving-throughput-probe-v2).

v2 re-measures the cells serving-throughput-probe-v1 did not deliver or
invalidated. It reuses the frozen v1 package (``harness.serving_probe``) for
prompts, screenshots, metric parsing and the Q2 budget rules, and adds:

* ``config``: the v2 contract loader (required and optional points, the
  largest-shape warm-up, the launch-window ledger's static check);
* ``contamination``: foreign-process identification by PID on the GPU and the
  engine's own footprint bounded by a reservation measured under the largest
  registered prompt shape;
* ``schedule``: the launch-window ledger (reserved time for required points,
  reruns and optional points from slack only);
* ``client``: the streaming client with prompt-token-id digests and fixed
  (prebuilt) replay history;
* ``x1``: the dummy-weight control on identical prompt token sequences.

``scripts/run_vllm_throughput_probe_v2.py`` owns engines, gates and persistence.
"""
