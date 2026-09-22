# Mini-HYV proof — manifest

| Path | Purpose |
|---|---|
| README.md | What ran, how to launch, communication honesty |
| MANIFEST.md | This file |
| config/agents.json | Five live local agent ids (no secrets) |
| config/personas/edwin.md | Edwin Research & Analysis identity and refusals |
| config/personas/agnes.md | Agnes Finance & Operations identity and refusals |
| config/.env.example | Env template, no keys |
| src/ask.py | Headless Letta Code client |
| src/run_proof.py | Five-agent identity, memory, routing, conflict |
| src/integration_map.md | Read-only map onto the current LifeOS tree |
| tests/test_agents_config.py | Offline check that five agent ids are present |
| evidence/five-agent/VERDICT.md | CONDITIONAL five-agent verdict |
| evidence/five-agent/COST.md | Services, models, tokens |
| evidence/five-agent/00-report.md | Human transcript summary |
| evidence/five-agent/00-report.json | Machine report |
| evidence/five-agent/01-identity-*.json | Live identity + refusal replies |
| evidence/five-agent/02-team-*.json | Custom-routed five-agent Quiet Ledger decision |
| evidence/five-agent/03-memory-*.json | Write + new-conversation recall |
| evidence/five-agent/04-isolation-*.json | Cross-department token isolation |
| evidence/five-agent/05-conflict-*.json | Financial vs creative disagreement |
| evidence/ | Original three-agent proof (unchanged history) |

Not included: `.venv/`, LifeOS website source, API keys, Letta Cloud, Council V2 files.
