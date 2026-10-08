"""Q2 Stage S1a (`q2-stage1-rescoped-v1`): analysis, plan and the G0 episode machinery.

Analysis (standard library plus numpy and scipy; reads records, starts nothing):

* ``estimators``: the registered estimators and randomization tests on an outcome array.
* ``records``: the episode-record schema the driver writes and the analysis sets built from it.
* ``rules``: the registered decision rules (DR0-DR5, DR-A) and the predictions P1-P5.
* ``plan``: caps, the A0-derived constants, CPU feasibility, task draw and episode orders.
* ``analysis``: the registered report, from records to every estimand, test and rule.

G0 items (registration section 3.1; they run VMs, containers and engines when invoked):

* ``driver``, ``agents``, ``engine``, ``osworld_live``: one episode in the episode container.
* ``lane`` (VM job), ``bridge`` (GPU job), ``fake_engine`` (tests and development only).
* ``rescore``, ``zinv``: offline rescoring and the corrected comparator.
* ``anchor``, ``glmm``: the anchor's CPU checks and the secondary model's input.
"""
