# VeriPatch — Maintenance Agent Skill

CodersJantaParty · Track 2. VeriPatch diagnoses maintenance failures in a public Python repository, prepares guarded exact diffs, requires human approval, verifies an isolated target copy, and exports a reproducible **Dependency Exit Capsule**.

**Final verified result:** actual LinkWatch commit `f52f3930c8e7c33d934ccf614955a38e26984bd5`: **10 original tests pass, 0 fail, 0 skip** after the reviewed repair. Report generation, dependency consistency and the actual replacement test workflow pass. All five original test files are byte-for-byte unchanged.

| Comparable profile v2 check | Baseline | Patched |
|---|---|---|
| Original suite | 9 pass / 1 fail / 0 skip | **10 pass / 0 fail / 0 skip** |
| pip check | exit 1 | **exit 0** |
| Nose compatibility | exit 1 | **exit 0: obsolete Nose retired** |
| Actual `make test-nose` invocation | exit 2 | **exit 0: same tests/ scope through pytest** |
| Explicit original report test | exit 1 | **exit 0** |
| Pydantic behavior contract | exit 0 | exit 0 |

All 12 fixed-profile commands pass after repair. Profile v2 was run on both sides; earlier v1 evidence remains separate. See [final validation](docs/evidence/final-validation.json), [the exact approved target patch](artifacts/target-maintenance.diff), and [the fresh capsule](artifacts/dependency-exit-capsule.zip).

## What was repaired

- Jinja2 declarations consistently become `>=3.1.6,<4`, repairing the removed MarkupSafe `soft_unicode` import failure.
- Both Pydantic declarations retain the previously reviewed `>=2.4.2` alignment. Source uses public v2 validators/configuration while preserving whitespace stripping, required values, HTTP scheme checks and forbidden extra settings.
- Obsolete Nose is replaced by pytest `>=8.3.5,<9`. The existing `make test-nose` target remains as a compatibility alias that runs the same `tests/` directory. Its actual invocation and README label are updated; no verification check or original test is removed.

These final edits are **maintainer-assisted**, approved by the user. They preserve the historical direct-Qwen Pydantic repair. A fresh bounded Qwen diagnosis genuinely ran, but its incorrect report/Pydantic advice was rejected and retained honestly. The final diff is not presented as a correct autonomous AI repair.

## Architecture and original contribution

React/TypeScript/Vite dashboard → Python 3.12/FastAPI coordinator → static inventory and direct-Qwen diagnosis/proposals → guarded diff/human approval → fixed LOCAL runner → evidence-linked issue status and capsule.

The actual **NousResearch Hermes Agent** provides bounded repository inspection and baseline-evidence tools. It runs separately with local Ollama `veripatch-qwen3.5:4b-64k`; a fresh real file-read tool execution and returned contents/hash are included. Hermes autonomous patch generation is disabled because it was unreliable. Direct Qwen uses installed `qwen2.5-coder:7b`. Models run sequentially, without cloud fallback.

Our contribution is the guarded maintenance workflow: source evidence, exact edits, safe paths, syntax/dependency preflight, protected original tests/configuration, explicit approval, comparable verification, issue-specific status, provenance and reusable capsules. Hermes supplies the existing open-source agent loop; Ollama/Qwen supply local inference. Historical and fresh calls retain their timestamps.

## Setup and usage

On the existing Mac installation, no new model or framework installation is needed:

```bash
cd /Users/nishi/Downloads/Developer/H26_CodersJantaParty_VeriPatch
PYTHONPATH=app app/.venv/bin/python -m veripatch serve
```

Open http://127.0.0.1:8000. Select run **6ff0dd**. Inspect **AI & patches**, **Verification**, **Agent activity**, **Findings**, then **Export capsule**. Every remaining observation has an evidence location and next action.

For a fresh application checkout, use Python 3.12, Node/npm and an existing local Ollama service:

```bash
python3.12 -m venv app/.venv
app/.venv/bin/pip install -r app/requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
PYTHONPATH=app app/.venv/bin/python -m veripatch serve
```

The built frontend is served with the API on loopback. Development frontend: `npm run dev --prefix frontend`. App dependencies are in `app/requirements.txt` and `frontend/package.json`. Hermes's official PM-managed Python 3.14 environment remains separate; see [setup, identity and tool evidence](docs/HERMES_SETUP.md). No cloud credentials are required. DigitalOcean is optional and unverified.

```bash
# Default direct-Qwen analysis; optional --commit FULL_SHA for exact reproduction.
PYTHONPATH=app app/.venv/bin/python -m veripatch analyze https://github.com/rishrek/LinkWatch --provider LOCAL
# Hermes inspection/baseline only, never patch generation.
PYTHONPATH=app app/.venv/bin/python -m veripatch analyze https://github.com/rishrek/LinkWatch --engine HERMES --provider LOCAL
PYTHONPATH=app app/.venv/bin/python -m veripatch plan RUN_ID
# Only after reviewing the exact displayed diff:
PYTHONPATH=app app/.venv/bin/python -m veripatch apply RUN_ID PROPOSAL_ID --approve
PYTHONPATH=app app/.venv/bin/python -m veripatch capsule RUN_ID --output capsule.zip
```

Models never choose shell commands or bookkeeping IDs. Supported proposals pass backend preflight and original-test protection. Makefile changes are limited to a literal Nose-to-pytest recipe migration preserving every other line and the exact test scope/options. LOCAL executes trusted target code in disposable venvs; it is not a security sandbox.

## Reproduce and demonstrate

[Short demo and reproduction guide](docs/HERMES_DEMO.md). Unzip [the capsule](artifacts/dependency-exit-capsule.zip) and follow `REPRODUCE.md`: clone the exact **target** commit, run baseline, apply its approved patch in that target clone, then run the same v2 profile. VeriPatch preserves the original target source in this checkout; target repairs are the reviewed patch/capsule, not an unreviewed overwrite of original files.

To display the published evidence in a fresh VeriPatch checkout without pretending to rerun it:

```bash
python3 - <<'PY'
import json, pathlib, zipfile
with zipfile.ZipFile('artifacts/dependency-exit-capsule.zip') as archive:
    record = json.loads(archive.read('capsule.json'))
folder = pathlib.Path('.veripatch') / record['id']
folder.mkdir(parents=True, exist_ok=True)
(folder / 'run.json').write_text(json.dumps(record))
PY
```

That restores recorded evidence for viewing/export only. Fresh verification is a separate explicit execution.

## Checks, limitations and licensing

**60 application tests pass**; frontend production build passes. One Starlette/httpx test-client deprecation warning remains.

```bash
PYTHONPATH=app app/.venv/bin/python -m pytest app/tests -q
npm run build --prefix frontend
```

Seven unchanged observations need review: HTTP timeout defaults, private Requests API, dynamic charset handling, global HTTP monkey patching, deprecated `pkg_resources`, a transitive-only certifi declaration, and URL authority validation (security, outside scored maintenance scope). Passing tests do not establish those observations are fixed. Dependencies are not transitively locked; actual resolved versions and logs are in the capsule. Hermes and Qwen can make incorrect recommendations; human review remains essential.

Project/original LinkWatch: [MIT license](LICENSE). Hermes `git.db44c46`: MIT. Qwen2.5-Coder 7B and Qwen3.5 4B: Apache-2.0. [Attribution and sources](ATTRIBUTION.md), [validation](docs/VALIDATION.md), [architecture](docs/ARCHITECTURE.md). No upstream push is authorized or performed.
