# Hermes inspection runtime and evidence

The existing Hermes/Ollama installation is retained. No new installation, model download or autonomous repair experiment is required for the working demo.

Hermes is official unmodified NousResearch source pinned to `db44c46208f1b421b4ecb7e56bf9d68b0423906f`; actual reported version `git.db44c46`, MIT. It lives under ignored `.hermes-runtime/source`. Its official PM-managed Python 3.14.7/dependency environment is separate from VeriPatch's Python 3.12 app environment. No Hermes dependencies were pip-installed into `app/.venv`.

Documented integration: `from run_agent import AIAgent`, `run_conversation`, and a plugin registered with `register(ctx)` / `ctx.register_tool`. The current plugin exposes only `inspect_repository`, `read_repository_file`, and `verify_repository`. There are no proposal, application, shell, browser or cloud tools. Actual historical failed-generation events remain in existing run records; disabling those capabilities does not erase the evidence.

The wrapper composes the already committed PM environment using Hermes's own activation helpers, verifies its freshness, then invokes official `scripts/run-in-hermes-env`. This avoids unnecessary network dependency resolution at runtime. Missing/stale environments fail with setup instructions rather than silently installing or switching models. Plugin configuration is set before importing `run_agent`, which discovers plugins during import.

## Actual compatibility evidence

This Mac has 16 GB RAM. Current Hermes enforces minimum 64,000 context. Installed `qwen2.5-coder:7b` has native 32K context and failed that guard. A metadata-only alias requesting 65,536 still served 32,768 and printed tool JSON without executing it. This was not counted as success, and Hermes's guard was not bypassed. The 7B model remains the working direct-Qwen repair model; it is not the Hermes inspection model.

After the user freed disk, Qwen3.5 4B was installed locally (4.0 GB download). Existing models were preserved. Alias `veripatch-qwen3.5:4b-64k` serves actual 65,536 context with Ollama 0.40.4's MLX runner. Digest: `806c7d026cf6f24e62ff603b194c8ed89c7a34491562d22c29d1ff549421498f`. Qwen model license: Apache-2.0.

Proof: `docs/evidence/hermes-compatibility.json` contains a real repository-read handler event, returned contents/SHA256, actual role=tool message and evidence-based final answer. `docs/evidence/ollama-served-context.json` records served context. Failed 7B evidence and exact proposal rejection diagnosis remain beside them. Retained timestamps are not a claim of new execution.

## Optional inspection command

```bash
PYTHONPATH=app app/.venv/bin/python -m veripatch analyze https://github.com/rishrek/LinkWatch --engine HERMES --provider LOCAL
```

This creates a real new inspection/baseline run only when explicitly invoked. The default dashboard/CLI repair engine is direct Qwen. `plan RUN_ID` uses direct Qwen over retained evidence. Models share a cross-process lock and run sequentially. Fallback providers, memory, lazy installs and deferred tool search are disabled. All services stay on loopback; no cloud credentials required.

The installation helper `scripts/setup-hermes.sh` is retained for future setup/reproduction, not run as part of this finalized demo. Official references consulted:
- https://hermes-agent.nousresearch.com/docs/getting-started/installation
- https://hermes-agent.nousresearch.com/docs/guides/local-ollama-setup
- https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration
- https://hermes-agent.nousresearch.com/docs/developer-guide/plugins
