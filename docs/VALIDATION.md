# Actual validation — 15 October 2026

This file records executed results, not fixture data or predetermined dashboard metrics.

## Application

- Python 3.12.5 on macOS ARM64; separate application virtual environment.
- Backend: **50 tests passed**. One Starlette TestClient deprecation warning recommends future migration from HTTPX to HTTPX2; it did not fail tests or the running API.
- Frontend: `tsc -b && vite build` succeeded (Vite 6.4.4).
- Application `pip check`: no broken requirements.
- Python source compilation and worker setup shell syntax checks passed.
- Browser checks: dashboard loads; real history, findings search, source evidence modal, AI diffs, executed baseline logs, unsupported URL rejection and empty state work. A 390 px viewport had document/body width 390 px (no horizontal page overflow); mobile history is available through Recent runs.
- Original LinkWatch source, tests, dependency files and MIT license are unchanged. Archived README SHA-256 equals the original: `67e48b13684fb5e08055515893e7f0b5f7c84f8d776d865a281606d3958ba6e2`.

## Real model integration

Ollama served **qwen2.5-coder:7b** locally at `http://127.0.0.1:11434`. A real schema-validated smoke response succeeded on its first attempt in 7.44 seconds. Actual repository analyses and integrated planning calls followed; successful responses are stored with model identity, timestamps, prompt hashes/context details when available, duration and Ollama token metrics.

Some initial batches failed issue-accounting validation or timed out. Those failures remain in real run history and the capsule. The implementation now bounds aggregate evidence/source/log context, preserves actual exception lines, includes actual resolved package metadata, constrains finding IDs in the response schema, and serializes model calls across processes. The measured integrated passes succeeded in 54.45 and 47.16 seconds. Qwen still returned incomplete or incorrect hypotheses; validation and execution expose those limits rather than fabricate a repair.

## Actual organizer-repository execution

Public source: https://github.com/rishrek/LinkWatch

Exact commit: `f52f3930c8e7c33d934ccf614955a38e26984bd5`

Primary retained run: `5f2114e6a2054299b50f3f8aaad0d4ab`

Provider: **LOCAL**, trusted-code runner. No cloud execution is claimed.

- Inventory: **24 supported files**, including **15 Python files**; **14 declared dependencies**; **2 skipped unsupported files**. Internal/dependency/generated directories are excluded as documented.
- Baseline inventory: **12 static observations** plus **3 actual command failures**, all retained as distinct findings/evidence records.
- Baseline original suite: **10 collected, 9 passed, 1 failed, 0 skipped**.
- Actual `pip check` failed on the conflicting Pydantic declaration versus the installed version.
- Actual Nose import failed with `ModuleNotFoundError: No module named 'imp'` on Python 3.12.
- The actual report-generation test failed because Jinja2 imported unavailable `markupsafe.soft_unicode`.

A real Qwen proposal (`P-d3c6699c60`) aligned the Pydantic constraints to `>=2.4.2` in both declarations. It was applied only to a separate disposable clone of the exact baseline commit. No upstream test was edited. The patched verification used a fresh target environment and the same command profile/provider.

| Check | Baseline | Patched |
|---|---|---|
| Dependency metadata (`pip check`) | exit 1 | **exit 0** |
| Nose compatibility import | exit 1 | exit 1 |
| Original test collection | 10 | 10 |
| Passed / failed / skipped | 9 / 1 / 0 | 9 / 1 / 0 |
| Static dependency conflicts | 2 observations | **0** |
| Overall verification | failed | failed |

There was no dropped test collection, added skip, weakened test or changed command scope. The overall repair is **not successful**: the report/Jinja2/MarkupSafe and Nose problems remain, along with other source observations. Source reinspection and exact execution support are retained. A later Qwen proposal merely swapped the incompatible constraints; the new static preflight rejected it before execution with `Patch retains referenced dependency conflicts: pydantic`.

## Capsule

An actual ZIP was exported and checked: **54 entries**, ZIP CRC check passed, all required JSON/report/reproduction/baseline/AI/verification artifacts present. It includes the real applied diff, original and patched command logs, AI failures and hypotheses, dependency inventory, coverage limits and unresolved concerns. No environment or Git-internal directory was exported. Unit tests also verify credential-pattern redaction and allowlisted secret exclusion.

Download from the running dashboard, or reproduce export with:

```bash
PYTHONPATH=app app/.venv/bin/python -m veripatch capsule 5f2114e6a2054299b50f3f8aaad0d4ab --output /private/tmp/VeriPatch-Dependency-Exit-Capsule.zip
```

Run artifacts live in gitignored `.veripatch/`; they are deliberately not embedded in the application or committed as fabricated future results.

## Blocked verification and next demo step

**DigitalOcean not configured.** No SSH host/key/agent access was supplied. The required worker integration, deployment script, identity checks, resource limits, failure handling and tests are implemented, but **actual DigitalOcean execution has not been demonstrated**. Local Docker is installed but its daemon is stopped, so no local Docker-container validation occurred either. LOCAL venv execution did run successfully as a mechanism and honestly reported target failures.

The next concrete hackathon action is to deploy the worker on an existing DigitalOcean Droplet using `docs/DIGITALOCEAN.md`, verify its SSH fingerprint, configure `.env`, restart the coordinator, run `worker-smoke`, then analyze and apply a reviewed proposal with provider DIGITALOCEAN. Capture genuine remote logs/capsule for the mandatory cloud demonstration. No billable resources were provisioned, no remote deployment was attempted without access, and no Git changes were pushed.
