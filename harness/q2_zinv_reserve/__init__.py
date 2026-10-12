"""Held-out validation of the corrected z-order comparator on the reserve split.

Registration ``q2-zinv-reserve-validation-v1`` (R03 (b) of the 2026-10-11 question-renewal
dossier), an addendum to ``q2-evaluator-mutation-v1``: the frozen operators build mutants of
the reserve split's pptx targets, the frozen pipeline saves and scores them, and the corrected
comparator ``compare_pptx_files_zinv`` (``harness/q2_stage1/zinv.py``, unchanged) rescores
every evaluable ``compare_pptx_files`` item beside the original.

* ``rules``: the registered constants, the decision rule (``judge``) and its power table.
* ``guard``: the freeze guard (standard library only; host and containers).
* ``run``: ``select-targets``, ``rescore`` and ``judge`` (the container steps).
"""
