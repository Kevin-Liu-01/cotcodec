#!/usr/bin/env bash
# CoTCodec Mac Mini Setup
# Run this on the Mac Mini to configure it as the always-on experiment runner.

set -euo pipefail

echo "=== CoTCodec Mac Mini Setup ==="

# 1. System dependencies
echo "→ Installing system dependencies..."
if ! command -v brew &> /dev/null; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
brew install python@3.11 git gh uv duckdb

# 2. Python project
echo "→ Setting up Python project..."
cd "$(dirname "$0")/.."
uv venv
uv pip install -e ".[dev]"

# 3. Local inference (MLX + Ollama)
echo "→ Installing local inference frameworks..."
uv pip install mlx mlx-lm
brew install ollama

echo "→ Pulling open-weight models (this takes a while)..."
ollama pull deepseek-r1:8b     # Distilled, fast for pilots
ollama pull qwen3:8b           # Multilingual
ollama pull llama4:8b           # Baseline

# 4. Benchmark repos
echo "→ Cloning benchmark repos..."
mkdir -p raw/baselines
git clone https://github.com/sierra-research/tau-bench.git raw/baselines/tau-bench 2>/dev/null || echo "  tau-bench already cloned"
git clone https://github.com/AlibabaResearch/DAMO-ConvAI.git raw/baselines/api-bank-source 2>/dev/null || echo "  API-Bank already cloned"

# 5. DuckDB for trace analysis
echo "→ Setting up DuckDB for trace analysis..."
python3 -c "
import duckdb
con = duckdb.connect('data/traces.duckdb')
con.execute('''
  CREATE TABLE IF NOT EXISTS experiments (
    experiment_id VARCHAR,
    benchmark VARCHAR,
    condition VARCHAR,
    model VARCHAR,
    task_id VARCHAR,
    seed INTEGER,
    success BOOLEAN,
    total_tokens INTEGER,
    total_latency_ms DOUBLE,
    cost_usd DOUBLE,
    tool_calls_correct INTEGER,
    tool_calls_total INTEGER,
    retries INTEGER,
    safety_failures INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  )
''')
print('  DuckDB initialized at data/traces.duckdb')
"

# 6. Cron jobs
echo "→ Setting up cron jobs..."
REPO_DIR="$(pwd)"
CRON_ENTRY="0 6 * * 1 cd $REPO_DIR && python3 -m automations.frontier_research >> research/scans/cron.log 2>&1"
(crontab -l 2>/dev/null | grep -v "frontier_research"; echo "$CRON_ENTRY") | crontab -
echo "  Weekly frontier research scan scheduled (Monday 6am)"

# 7. API key check
echo ""
echo "=== Manual Steps Required ==="
echo "1. Set API keys in .env:"
echo "   ANTHROPIC_API_KEY=sk-ant-..."
echo "   OPENAI_API_KEY=sk-..."
echo "   DEEPSEEK_API_KEY=sk-..."
echo "   GOOGLE_API_KEY=..."
echo ""
echo "2. Set up SSH access from your laptop:"
echo "   ssh-copy-id mac-mini.local"
echo ""
echo "3. Set up Tailscale for remote access:"
echo "   brew install tailscale"
echo "   sudo tailscale up"
echo ""
echo "4. Verify Ollama models loaded:"
echo "   ollama list"
echo ""
echo "=== Setup Complete ==="
