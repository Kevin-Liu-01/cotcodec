"""K2 VM-fidelity executor of q2-evaluator-mutation-v1 (addendum q2-evaluator-mutation-v1-k2).

Injects a checker-mutation candidate into the certified OSWorld VM, saves it through the VM's
LibreOffice as the pipeline does, scores it with the pinned checker and compares the in-VM
verdict with the offline harness's (registration ``q2-evaluator-mutation-v1-k2``).
"""
