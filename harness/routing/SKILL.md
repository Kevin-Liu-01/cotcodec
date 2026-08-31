---
name: harness-routing-skill
description: Procedure for past-only message feature extraction and dynamic orchestration policy selection.
---

# cotcodec / harness/routing

## Purpose
<!-- agent-docs:fill:purpose -->

Routing chooses an orchestration condition per visible message from explicit,
auditable features rather than using one condition globally.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `features.py` extracts message/state features available at decision time.
- `policy.py` maps those features to a condition and records the decision.
- Optimization and evaluation live outside the online policy so frozen policies
  remain reproducible.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Features must be available strictly before the routed outcome.
- Record feature values, policy version/hash, selected arm, and fallback reason.
- Keep a fixed-condition baseline and charge routing overhead to the routed arm.
- Fail closed or use a preregistered fallback for unknown message types.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

- Feature change: prove no future-label leakage and update serialization tests.
- Policy change: freeze a new version and compare against fixed-arm baselines.

## Gotchas
<!-- agent-docs:fill:gotchas -->

- A router trained and evaluated on the same tasks is not a valid routing result.
- Model self-reports are not free features; count their tokens, latency, and risk.
