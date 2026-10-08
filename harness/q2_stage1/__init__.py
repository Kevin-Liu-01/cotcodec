"""Q2 Stage S1a (`q2-stage1-rescoped-v1`): plan, estimators, records and decision rules.

* ``estimators``: the registered estimators and randomization tests on an outcome array.
* ``records``: the episode-record schema the driver writes and the analysis sets built from it.
* ``rules``: the registered decision rules (DR0-DR5, DR-A) and the predictions P1-P5.
* ``plan``: caps, the A0-derived constants, CPU feasibility, task draw and episode orders.
* ``analysis``: the registered report, from records to every estimand, test and rule.

Standard library plus numpy and scipy. Nothing here starts a job or touches a VM.
"""
