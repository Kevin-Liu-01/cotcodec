---
name: fertility-check
version: 0.1.0
triggers: ["fertility", "tokenizer", "token count", "new model fertility"]
tools: [shell, read, write]
mutating: true
---

# Fertility Check

Measure tokenizer fertility for a model across target languages.

## Contract

Given a model name, this skill:
1. Loads or generates parallel text samples (planning text, memory summaries, etc.)
2. Counts tokens across English, Chinese, Korean, Polish, Russian, Japanese
3. Computes fertility ratios
4. Writes results to `data/tokens/{model}_fertility.json`
5. Updates `memory.json` landscape tracking

## Steps

1. Check if parallel corpus exists at `data/tokens/parallel_corpus.json`
   - If not, generate 20 samples from agent message categories
2. Load the model's tokenizer (tiktoken for GPT, anthropic API for Claude)
3. Count tokens for each (sample, language) pair
4. Compute mean fertility and standard deviation per language
5. Write results
6. Compare against existing models — flag notable differences

## Output Format

| Language | Fertility (mean) | Std Dev | vs English |
|----------|-------------------|---------|------------|
| Chinese  | 0.79              | 0.05    | -21% tokens |
| Korean   | 0.56              | 0.08    | -44% tokens |
| Polish   | 1.62              | 0.12    | +62% tokens |
