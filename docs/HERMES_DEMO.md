# Working review → verify → export demo

Run `8f5c766cc3e34bfeb359784bfe42d70b`, actual LinkWatch commit `f52f3930c8e7c33d934ccf614955a38e26984bd5`.

## Short demo script

1. Start `PYTHONPATH=app app/.venv/bin/python -m veripatch serve`, then open http://127.0.0.1:8000. Select LinkWatch run **8f5c76** (created 15 October 2026 at 15:08 IST). Other retained runs include failures; do not confuse them with this approved replay.
2. Open **Agent activity**. Show actual Hermes inventory/read/baseline tool calls, results and original timestamps. Explain that failed repair-generation history is retained and generation is now disabled; these are not new live executions.
3. Open **AI & patches**. Show **Recovered direct-Qwen repair: align Pydantic constraints**, ID `Q-d3c6699c60`, its authorship and exact diff. Both manifests change to `pydantic>=2.4.2`.
4. Explain that the user explicitly approved this diff. The **Approve patch & verify** button is the approval action for future pending proposals; this already-applied proposal is no longer pending. The backend records the approved diff hash and executes the fixed LOCAL runner in a separate clone.
5. Open **Verification**. Baseline/patched collect the same 10 tests: 9 pass, 1 fails, 0 skip. `dependency-check` changes exit 1 → 0. Nose compatibility and the report test still fail. Show those actual logs. The full profile is not passing.
6. Open **Findings**: the two Pydantic conflict observations and dependency-check failure are fixed with supporting evidence; other issues remain unresolved/need review. All five original test files have identical before/after SHA-256 hashes.
7. Select **Export capsule**. Inspect `REPORT.md`, `REPRODUCE.md`, `capsule.json`, patch, original/patched logs, approval, Hermes activity and historical Qwen provenance.

Saved fresh capsule: `.veripatch/8f5c766cc3e34bfeb359784bfe42d70b/dependency-exit-capsule.zip`.
Detailed measured summary: `docs/evidence/direct-qwen-approved-replay.json`.

## Exact provenance

Hermes inspection: official unmodified `git.db44c46`, commit `db44c46208f1b421b4ecb7e56bf9d68b0423906f`, MIT. It actually selected tools and received repository contents and baseline results. Inspection model: local `veripatch-qwen3.5:4b-64k`, digest `806c7d026cf6f24e62ff603b194c8ed89c7a34491562d22c29d1ff549421498f`, actual served context 65,536.

Repair authorship: historical **direct Ollama Qwen2.5-Coder 7B** proposal `P-d3c6699c60`, source run `5f2114e6a2054299b50f3f8aaad0d4ab`, response timestamp `2026-10-15T08:04:02.030463+00:00`. Its exact edits/diff match the current target commit and passed preflight before approval. Recovery is not new model inference. The model's old unverified “latest version” claim is retained in provenance but is not asserted as fact.

The approved replay ran fresh LOCAL verification. It did not invoke Hermes or Qwen. Before/after command scope, collection and skip counts match. Capsule replay uses the exact recorded diff rather than expecting stochastic model output to repeat.

## Current limitations

- Hermes autonomous patch generation produced malformed/incorrect proposals and is disabled. Failure events remain intact, including exact argument/schema rejections in `docs/evidence/hermes-rejection-diagnosis.json`.
- Nose 1.3.7 imports removed `imp`; Jinja2 2.11.3/MarkupSafe breaks report generation. The original failing test remains intact.
- Other static findings include legacy Pydantic validators, private/deprecated APIs, dynamic codec handling, prefix-only URL validation, global HTTP monkey patching, missing timeout and an undeclared import. They are not claimed fixed by a dependency repair.
- LOCAL venv execution trusts target code; it is not a security sandbox. Dependencies are not locked transitively; actual resolved versions are in the logs. DigitalOcean is optional and unverified.

## Reproduction

Unzip the capsule and follow `REPRODUCE.md` to clone the exact target commit, execute baseline, apply `patches/Q-d3c6699c60.diff`, and run the identical profile. Do not edit or suppress original tests. Use fresh destination directories.
