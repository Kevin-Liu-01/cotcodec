# Variable 6: Planning Depth

**Status:** Unexplored. Connects to the overthinking literature. Paper 3 candidate.

## The Variable

σ = planning ∈ {no_plan, one_step_lookahead, full_plan_then_act, iterative_refinement, hierarchical_decomposition}

How far ahead should the agent plan before taking its first action?

## Why It Matters

Cuadron et al. show that overthinking hurts agent performance — too much
planning before acting wastes tokens and can lead the agent astray. But
too little planning causes agents to take wrong actions and waste tokens
on retries. The optimal depth is task-dependent and no one has measured
where the crossover is.

## Conditions to Test

| Depth | Description |
|-------|-------------|
| No plan (ReAct) | Reason-act alternation, one step at a time |
| 1-step lookahead | Plan the next action only, then act |
| Full plan | Plan all steps, then execute sequentially |
| Iterative refinement | Plan, execute 1-2 steps, re-plan with new info |
| Hierarchical | Decompose into subtasks, plan each independently |

## Key Hypotheses

1. Iterative refinement dominates — plan enough to start, then re-plan
   with real information
2. Full planning wastes tokens on tasks where tool outputs are unpredictable
3. No-plan (pure ReAct) wastes tokens on tasks requiring coordination
   across multiple tools
4. Hierarchical decomposition helps long tasks but hurts short ones (overhead)

## Connections

- **Reasoning format** — structured plans are shorter and more actionable
- **Language** — planning text is the highest-compression target for language routing
- **Retry** — bad plans cause retries. Better planning reduces retry budget.
