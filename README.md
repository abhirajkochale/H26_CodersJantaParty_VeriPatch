# VeriPatch

VeriPatch provides a working **direct-Qwen proposal → human approval → isolated LOCAL verification → Dependency Exit Capsule** workflow. The actual NousResearch Hermes Agent is retained for repository inspection and baseline verification, with real tool evidence. Hermes patch generation is disabled: its autonomous repair proposals were unreliable. These roles and their timestamps remain separate in the dashboard and capsule.

The original LinkWatch code, tests and MIT license are preserved. Its README is archived in [docs/UPSTREAM_README.md](docs/UPSTREAM_README.md). No cloud credentials or DigitalOcean deployment are required.

## Demonstrated result

Actual target: `https://github.com/rishrek/LinkWatch`, commit `f52f3930c8e7c33d934ccf614955a38e26984bd5`.

The user approved recovered direct-Qwen proposal `Q-d3c6699c60`: change both Pydantic declarations to `>=2.4.2`. It is the exact earlier Qwen2.5-Coder 7B proposal from run `5f2114e6a2054299b50f3f8aaad0d4ab`, not a new inference or Hermes-authored patch. Fresh LOCAL verification ran in a separate clone/environment.

| Check | Baseline | Approved patch |
|---|---|---|
| pip check | exit 1 | **exit 0** |
| Original test collection | 10 | 10 |
| Original tests | 9 passed / 1 failed | 9 passed / 1 failed |
| Skipped tests | 0 | 0 |
| Nose compatibility | exit 1 | exit 1 |

The dependency conflict is fixed; the complete profile still fails. Nose imports removed `imp` on Python 3.12, and report generation fails because Jinja2 2.11.3 imports removed MarkupSafe `soft_unicode`. All five original test files have identical SHA-256 hashes before/after. Other detected issues remain unresolved or need review. [Measured evidence](docs/evidence/direct-qwen-approved-replay.json) and [demo instructions](docs/HERMES_DEMO.md) give the exact details.

Fresh capsule: `.veripatch/8f5c766cc3e34bfeb359784bfe42d70b/dependency-exit-capsule.zip`.

## Start the existing local installation

```bash
cd /Users/nishi/Downloads/Developer/H26_CodersJantaParty_VeriPatch
PYTHONPATH=app app/.venv/bin/python -m veripatch serve
```

Open http://127.0.0.1:8000. Ollama should already run on loopback. The installed repair model is `qwen2.5-coder:7b`; optional Hermes inspection uses the installed `veripatch-qwen3.5:4b-64k` model. Models are serialized, with no cloud fallback. No new installation or download is needed for this demo.

For a fresh application installation: Python 3.12 venv at `app/.venv`, `pip install -r app/requirements.txt`, then `npm ci --prefix frontend` and `npm run build --prefix frontend`. Hermes stays in a separate official PM-managed Python 3.14 environment; see [docs/HERMES_SETUP.md](docs/HERMES_SETUP.md). Do not install it into the app environment.

## Workflow and CLI

The dashboard defaults to direct Qwen repair planning. **AI & patches** shows provenance, exact diffs, uncertainty and **Approve patch & verify**. **Agent activity** retains actual Hermes inspection and failed-generation history, explicitly labeled as retained evidence. **Verification** shows actual command logs and before/after counts. **Export capsule** downloads current evidence.

```bash
# New direct-Qwen run (default); records the exact source commit.
PYTHONPATH=app app/.venv/bin/python -m veripatch analyze https://github.com/rishrek/LinkWatch --provider LOCAL
# Optional Hermes inspection/baseline only; no patch tools exposed.
PYTHONPATH=app app/.venv/bin/python -m veripatch analyze https://github.com/rishrek/LinkWatch --engine HERMES --provider LOCAL
# Plan a direct-Qwen repair from retained evidence.
PYTHONPATH=app app/.venv/bin/python -m veripatch plan RUN_ID
# Explicit approval after reviewing the displayed exact diff.
PYTHONPATH=app app/.venv/bin/python -m veripatch apply RUN_ID PROPOSAL_ID --approve
PYTHONPATH=app app/.venv/bin/python -m veripatch capsule RUN_ID --output capsule.zip
```

`--commit FULL_SHA` selects an exact target revision. CLI and dashboard share atomic `.veripatch/` state and an operation lock. Exact-match/preflight checks, protected tests/configuration, explicit approval, fixed command profiles and collection/skip comparisons remain enforced. At most three approved repair attempts are allowed.

LOCAL executes trusted target code in disposable Python 3.12 venvs; it is not a security sandbox. DigitalOcean remains optional and has never been demonstrated. Existing cloud code is retained; it is not used by this demo.

## Checks and attribution

```bash
PYTHONPATH=app app/.venv/bin/python -m pytest app/tests -q
npm run build --prefix frontend
```

Current checks: **59 application tests pass** (one Starlette/httpx deprecation warning); frontend production build passes. Original upstream tests are verified separately in the target runner, never deleted, skipped or weakened to manufacture success.

Original contribution: guarded maintenance tools, explicit review/approval, isolated fixed verification, evidence-linked issue inventory and reusable capsules. Hermes supplies the existing open-source agent/tool loop (MIT, `git.db44c46`); Qwen models supply local inference (Apache-2.0). See [ATTRIBUTION.md](ATTRIBUTION.md), [architecture](docs/ARCHITECTURE.md), [Hermes setup/evidence](docs/HERMES_SETUP.md), and [validation](docs/VALIDATION.md). No GitHub push was performed.
