# Variable 4: Context Allocation

**Status:** Unexplored. Subsumes several other variables. Paper 2-3 candidate.

## The Variable

σ = allocation ∈ {fixed_proportions, dynamic_budget, priority_weighted, adaptive}

The question: how should the agent divide its context window budget across
competing demands?

## The Budget Problem

A 200K-token context window sounds enormous. In practice, a tool-using agent
splits it across:

| Component | Typical % | Compressible? |
|-----------|----------|---------------|
| System prompt + instructions | 5-15% | Partially (structured formats help) |
| Tool schemas | 10-30% | No (tools need exact schemas) |
| Working memory / history | 20-40% | Yes (the main target) |
| Current reasoning | 10-20% | Yes (language/format help) |
| Tool observations | 10-30% | Yes (can truncate or summarize) |
| Safety buffer | 5-10% | No |

Most systems allocate these implicitly. The MCP SDK at Dedalus, for example,
includes all tool schemas in every call — even tools unlikely to be used.
That's a context allocation decision nobody made consciously.

## Conditions to Test

| Policy | Description |
|--------|-------------|
| Fixed proportions | Hard caps: 20% tools, 40% memory, 20% reasoning, 20% observations |
| Dynamic budget | Shift budget toward the most active component |
| Priority-weighted | User-defined priorities (e.g., tool schemas > old observations) |
| Adaptive | Learn allocation from trajectory performance |

## Key Hypotheses

1. Dynamic allocation outperforms fixed — short tasks need more tool schemas,
   long tasks need more memory budget
2. Reducing tool schema allocation (only include relevant tools) has
   outsized impact because schemas are dense and incompressible
3. Context allocation interacts multiplicatively with other variables —
   better language + better allocation compounds

## Connections

- **Language** — language choice is a way to compress one budget component
- **Memory** — memory policy determines how much of the memory budget is useful
- **Observation granularity** — how much tool output to keep is an allocation question
- **Tool scheduling** — which tools to include is an allocation question
