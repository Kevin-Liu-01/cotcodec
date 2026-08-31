#!/usr/bin/env npx tsx
/**
 * Agent-Docs Mesh shim — forwards to the canonical kit in kevin-wiki.
 * Override: KEVIN_WIKI_ROOT=/path/to/kevin-wiki
 */
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const wikiCandidates = [
  process.env.KEVIN_WIKI_ROOT,
  join(homedir(), "Documents/GitHub/kevin-wiki"),
  join(homedir(), "repos/Kevin-Wiki-v3"),
].filter((candidate): candidate is string => Boolean(candidate));
const wikiRoot = wikiCandidates.find((candidate) =>
  existsSync(join(candidate, "scripts/agent-docs/index.ts")),
);
if (!wikiRoot) {
  console.error(
    "agent-docs: canonical wiki kit not found. Set KEVIN_WIKI_ROOT to the kevin-wiki checkout.",
  );
  process.exit(2);
}
const kit = join(wikiRoot, "scripts/agent-docs/index.ts");
const tsx = join(wikiRoot, "node_modules/.bin/tsx");
if (!existsSync(tsx)) {
  console.error(
    "agent-docs: canonical wiki dependencies are missing. Run npm install in the wiki checkout.",
  );
  process.exit(2);
}

const r = spawnSync(
  tsx,
  [kit, ...process.argv.slice(2)],
  { stdio: "inherit" },
);
process.exit(r.status ?? 1);
