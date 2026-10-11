"""Q2 design study (D66): a seeded simulator fitted to S1a's records.

CPU only. It fits the variance components that drive S1a's estimands from the committed
episode records (``data``, ``fit``), generates S1a-shaped data for arbitrary designs
(``model``), analyses them with the registered estimators and decision rules imported
unchanged from ``harness.q2_stage1`` (``analyse``), and prices designs from S1a's realized
cost (``cost``). Nothing here is code of record for S1a; ``harness/q2_stage1`` stays frozen.
"""
