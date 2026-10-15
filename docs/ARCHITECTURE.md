# Architecture and module guide

Browser React/TypeScript dashboard → loopback FastAPI coordinator → atomic JSON state, disposable Git clones, static inspector, local Ollama Qwen. Verification → either explicitly labeled trusted LOCAL Python 3.12 runner or SSH → existing DigitalOcean Droplet → disposable Docker Python 3.12 execution. No direct browser-to-Ollama access is required.

## Modules

- `app/veripatch/inspection.py`: walks supported repository files, reports exclusions, parses Python AST, PEP 508 requirements and TOML. Records all detected findings and every parsed dependency, declarations, markers, usage, disposition and unknown metadata. Proves simple constraint conflicts; returns unknown when it cannot prove a result.
- `ai.py`: serializes bounded evidence/source/log batches, asks actual Qwen for schema-constrained output, validates Pydantic models and issue accounting, allows one corrective retry, records model/timing/prompt-hash/source-context provenance, and serializes requests across processes. Repository text is untrusted data.
- `patches.py`: validates relative paths, extensions, no symlinks, exact single matches, protected tests and sensitive paths. Builds unified diffs and applies a fully prevalidated proposal to a fresh baseline clone. No model shell commands are accepted.
- `execution.py`: fixed SSH protocol and local runner, worker identity validation, equivalent-profile comparison, collection/skip regression detection. Each selected proposal is an alternative applied to a fresh baseline copy; proposals are not silently stacked.
- `service.py`: background single-operation job executor, exact Git commit provenance, stages, independent AI batch failures, baseline and patched verification, source reinspection, explicit errors. The integrated planning action asks Qwen to combine interacting runtime failures and declaration conflicts in one bounded evidence batch.
- `store.py`: atomic fsync/replace state persistence and cross-process file locking. State lives in `.veripatch/`, outside the upstream application.
- `capsule.py`: allowlisted ZIP export; separate baseline/AI/verification, source evidence, dependency usage, recommendations, diffs and reproduction. Repository files, environments, credentials and private configuration are excluded; known secret patterns are redacted.
- `api.py`: local REST API, asynchronous operations with polling, runtime connection checks, downloads and built dashboard hosting. Origin checks protect mutation endpoints against cross-site requests; run only on loopback.
- `__main__.py`: startup, real integration smoke checks, analyze/apply/list/export CLI, optional `.env` parsing without shell execution.
- `worker/server.py`: fixed stdin/stdout JSON protocol, DigitalOcean metadata check, exact commit/hash validation, per-job directories and bounded Docker execution/cleanup.
- `worker/execute.py`: same fixed Python 3.12 profile for LOCAL and Docker. Records each command and redacted logs; test probe records actual counts without modifying upstream tests.
- `frontend/src`: responsive dashboard with live history, filterable findings, dependency coverage, AI diffs, logs and export.

## Fixed verification profile

1. Create separate Python 3.12 target environment.
2. Install fixed pytest tooling.
3. Install root `requirements*.txt` together, if present (including development requirements).
4. Install project with `pip install --no-deps .` when packaging exists; dependencies are kept from the explicit requirements environment.
5. `pip check`: exposes installed-package metadata inconsistencies.
6. Record `pip list --format=json` resolved versions.
7. Compile Python sources.
8. Import Nose if installed to expose actual Python compatibility. Absence is reported explicitly.
9. `pytest --collect-only`, then the original `pytest -q -ra` suite, with a read-only observation plugin outside repository source.

All commands record cwd, argv, Python runtime, exit code, stdout, stderr, duration, timeout and truncation. Installation failure does not suppress later diagnostic checks. No arbitrary model commands are executed. The execution profile is intentionally narrow; project manifests and requirements are not two independent environments. No lockfile means transitive dependency resolution may differ over time; installed versions are recorded.

## What success means

Analysis completion means the workflow produced its artifacts, including failures. Verification success requires all fixed commands to succeed, nonzero test collection, no dropped tests or increased skips, equivalent command scope and provider. A linked source observation is only marked `checks_passed` after static reinspection no longer finds that rule on that file. Passing tests do not independently prove every finding repaired. Runtime-failure findings remain `needs_review` even with a passing suite.

## Supported scope and limitations

Python AST, root requirements installation, PEP 508 constraints, PEP 621 dependency metadata and pytest are supported. Nested requirements are inventoried but not independently installed; recursive include/options or unsupported declarations are reported. Poetry/PDM/Conda/npm manifests do not receive dependency semantics. Dynamic imports, aliases beyond the small explicit mapping, arbitrary bugs, external service tests and all possible API deprecations are not exhaustive. Most metadata is deliberately unknown unless execution establishes it. There is no package-age or vulnerability score.

Files above 160 KB, binary/non-UTF8 files, sensitive filenames, symlinks and dependency/internal directories are excluded and reported. Individual source context and logs are bounded; source truncation can require manual review. Model batches may propose conflicting alternatives; validation rejects stale/ambiguous edits. Test results are generated by target code and should be treated as untrusted evidence. Regex redaction reduces known token exposure but cannot prove absence of every secret format. Do not analyze private/credential-bearing repositories with the trusted LOCAL runner.

The coordinator is a local developer tool, not a multi-tenant hosted service. It has no account authentication, production quota management, cancellation or remote API exposure. DigitalOcean credentials are intentionally not shipped. Cloud integration must be demonstrated with real access before submission claims are made.
