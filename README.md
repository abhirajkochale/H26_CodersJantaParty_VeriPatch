# VeriPatch

**CodersJantaParty · Track 2: Maintenance Agent Skill**

VeriPatch inspects a public Python repository, records an executed baseline, asks local Qwen for evidence-backed repair proposals, applies a selected exact-match patch in a separate clone, reruns the same checks, and exports a reusable **Dependency Exit Capsule**.

The original LinkWatch source, tests, dependency declarations and MIT license are preserved. Its original README is archived at [docs/UPSTREAM_README.md](docs/UPSTREAM_README.md). VeriPatch's application environment is separate from LinkWatch.

## Start on macOS

From this checkout (the path below is the actual workspace):

```bash
cd /Users/nishi/Downloads/Developer/H26_CodersJantaParty_VeriPatch
python3.12 -m venv app/.venv
app/.venv/bin/pip install -r app/requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
cp .env.example .env
```

Ollama must already serve the configured model locally:

```bash
ollama serve
# In another terminal, if the model is not already installed:
ollama pull qwen2.5-coder:7b
```

Start the coordinator and built dashboard together:

```bash
PYTHONPATH=app app/.venv/bin/python -m veripatch serve
```

Open **http://127.0.0.1:8000**. The server binds to loopback. Ollama stays on loopback; do not expose it publicly. For frontend development, run `npm run dev --prefix frontend` in another terminal and open http://127.0.0.1:5173.

## CLI

```bash
PYTHONPATH=app app/.venv/bin/python -m veripatch model-smoke
PYTHONPATH=app app/.venv/bin/python -m veripatch analyze https://github.com/rishrek/LinkWatch --provider LOCAL
PYTHONPATH=app app/.venv/bin/python -m veripatch list
PYTHONPATH=app app/.venv/bin/python -m veripatch plan RUN_ID
PYTHONPATH=app app/.venv/bin/python -m veripatch apply RUN_ID PROPOSAL_ID
PYTHONPATH=app app/.venv/bin/python -m veripatch capsule RUN_ID --output /private/tmp/veripatch-capsule.zip
```

`analyze --commit FULL_SHA` reproduces an exact commit. The dashboard analyzes current HEAD and records its exact SHA. No model response or target finding is pre-generated or hardcoded. CLI and UI share `.veripatch/` state; only one mutating operation may run at a time, including across coordinator processes.

**LOCAL runs trusted target code on your Mac in a disposable Python 3.12 virtual environment. A venv is not a security sandbox.** Use the DigitalOcean container worker for untrusted code. Both modes install dependencies and execute target tests. All execution is explicitly labeled with its actual provider.

## DigitalOcean is part of the architecture

An existing DigitalOcean Linux Droplet runs the fixed SSH worker. It clones the exact commit, validates and hashes edits, installs target dependencies and executes baseline/patched checks inside resource-limited disposable Python 3.12 Docker containers. Results include the Droplet ID from metadata, container image ID, command logs, exit codes, runtime, durations and test counts.

No Droplet is provisioned automatically. Without access the app displays **“DigitalOcean not configured.”** No local result is relabeled as cloud execution. Follow [docs/DIGITALOCEAN.md](docs/DIGITALOCEAN.md), configure `.env`, restart the coordinator, run `worker-smoke`, then choose DigitalOcean in the dashboard. Real cloud validation is required before claiming the mandatory integration was demonstrated.

## Checks

```bash
PYTHONPATH=app app/.venv/bin/python -m pytest app/tests -q
npm run build --prefix frontend
PYTHONPATH=app app/.venv/bin/python -m veripatch model-smoke
PYTHONPATH=app app/.venv/bin/python -m veripatch worker-smoke
```

Use **app/tests**, not the preserved upstream `tests/`, for application tests. Upstream tests are exercised separately inside each target run. See [docs/VALIDATION.md](docs/VALIDATION.md) for actual measured results and missing access.

## What the dashboard provides

Repository input and real run history; Ollama/worker connection checks; backend stages; supported-file coverage and skipped-file reasons; dependency declarations and import usage; filterable evidence-linked findings; runtime Qwen recommendations, an integrated baseline-repair planning pass, and readable diffs; isolated apply-and-verify; baseline/patched command logs and test counts; and a downloadable ZIP with JSON, report, patches, logs and reproduction steps.

Evidence status (`source_observed`, `execution_verified`, `ai_hypothesis`) is separate from repair status (`unresolved`, `proposed`, `applied`, `checks_passed`, `failed`, `needs_review`). A successful analysis is never presented as a successfully repaired repository. A passing suite supports only the executed profile. Static reinspection is required before an associated source observation is marked `checks_passed`; runtime findings still require review.

## Model, licenses, references

Qwen2.5-Coder 7B is an open-weight code model by the Qwen team, accessed through Ollama tag `qwen2.5-coder:7b`, `POST /api/chat`, with schema-based `format`, `stream:false`, low temperature, 8K context, bounded source/log batches, explicit timeouts and at most one corrective structured-output retry. Qwen performs runtime root-cause explanation, repair planning, exact edits, regression suggestions and uncertainty assessment. VeriPatch does not train or fine-tune it.

- [Qwen model card and Apache 2.0 license](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)
- [Official Qwen2.5-Coder release and license description](https://qwenlm.github.io/blog/qwen2.5-coder/)
- [Ollama model distribution](https://ollama.com/library/qwen2.5-coder)
- [Organizer's original LinkWatch](https://github.com/rishrek/LinkWatch)
- [Submission repository](https://github.com/abhirajkochale/H26_CodersJantaParty_VeriPatch)

Application additions use MIT, see [LICENSE-VERIPATCH](LICENSE-VERIPATCH). Upstream copyright and [LICENSE](LICENSE) remain intact. Third-party notices and roles: [docs/ATTRIBUTION.md](docs/ATTRIBUTION.md).

Read [architecture and module guide](docs/ARCHITECTURE.md), [presentation and demo](docs/PRESENTATION.md), and [DigitalOcean deployment](docs/DIGITALOCEAN.md) for team handoff.
