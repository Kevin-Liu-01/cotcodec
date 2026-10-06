# Portable orchestration capsules

This package is a research instrument, not a claim that CoTCodec invented agent
middleware. AgentHarnessProtocol, Agent Control Specification, HarnessX, AG2,
Vercel HarnessAgent, and other systems already expose portable events,
processors, or adapters.

The narrower question is whether one fixed orchestration behavior can be
realized across heterogeneous hook systems without semantic drift.

A capsule declares:

- lifecycle hooks it must observe;
- effects the host must enforce;
- state lifetime and action budget;
- deterministic event-to-action behavior.

An adapter publishes a `CapabilityManifest`. `compile_capsules` refuses a host
that lacks any required hook or effect. It never silently degrades a memory,
verification, retry, or safety policy into telemetry-only behavior.

Dispatch is prepare/validate/commit for stateful capsules. If composition or
host validation rejects an event, staged state is rolled back before the error
escapes.

The current reference capsules are:

- `MemoryGraphCapsule`: session-scoped provenance graph over tool observations,
  with bounded lexical recall and explicitly untrusted/data-only injection;
- `VerifyBeforeFinalCapsule`: blocks finalization until structured verification
  evidence is present.

They run only over framework-visible events. Hidden chain-of-thought is neither
required nor captured. Concrete AHP, LangChain, OpenAI Agents SDK, AG2, and
Vercel adapters remain future work and must each pass replay-parity and live
conformance tests before portability is claimed.
