"""vLLM serving-throughput probe (experiment serving-throughput-probe-v1).

The package holds the CPU-testable parts of the probe: the contract loader,
synthetic prompt and screenshot builders, the streaming OpenAI-chat client and
closed-loop episode replay, metric parsing and the budget projection rules.
``scripts/run_vllm_throughput_probe.py`` owns engine lifecycle, gates and
persistence, and imports vLLM, torch and Triton only inside the container.
"""
