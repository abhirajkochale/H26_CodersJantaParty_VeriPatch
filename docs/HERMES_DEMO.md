# Final demo and reproduction

Target https://github.com/rishrek/LinkWatch at `f52f3930c8e7c33d934ccf614955a38e26984bd5`. Demonstration run **6ff0dd70641c4f0abc837206baba5ff4**; approved proposal **M-final-maintenance**.

## 90-second demo

1. Start `PYTHONPATH=app app/.venv/bin/python -m veripatch serve`; open http://127.0.0.1:8000 and select **6ff0dd**.
2. **AI & patches:** show maintainer-assisted authorship, exact reviewed diff and approval record. Explain that Qwen supplied a real diagnostic review, with incorrect advice rejected; the historical Pydantic repair is separately attributed to direct Qwen. The user approved runtime edits and the README correction before application.
3. **Agent activity:** show `fresh_bounded_inspection`, the actual Hermes `repository_read` arguments, returned requirements contents/SHA256 and actual role=tool message in the capsule. Historical failed-generation activity retains original timestamps. No patch generation is enabled.
4. **Verification:** show comparable v2 baseline vs patched: **9/10 → 10/10 passing, 0 skips**; pip check exit **1 → 0**, legacy Makefile workflow **2 → 0**, explicit report test **1 → 0**. All 12 commands now pass. Original five test files have identical hashes; separate Pydantic behavior checks pass on both sides.
5. **Findings:** 12 observations fixed with support; seven unchanged observations need review and have specific next actions. Security scope is marked separately. This is not exhaustive bug discovery.
6. **Export capsule:** open `REPORT.md`, `capsule.json`, `REPRODUCE.md`, approved diff, command logs, agent/model identities, approvals, fresh Qwen review and fresh Hermes tool evidence.

Fresh capsule: [artifacts/dependency-exit-capsule.zip](../artifacts/dependency-exit-capsule.zip). Exact patch: [artifacts/target-maintenance.diff](../artifacts/target-maintenance.diff). Local run also retains `.veripatch/6ff0dd70641c4f0abc837206baba5ff4/dependency-exit-capsule.zip`.

## Exact measured results

| v2 check | Baseline exit | Patched exit |
|---|---:|---:|
| create-env / tooling / installs | 0 | 0 |
| dependency-check | 1 | 0 |
| resolved-packages / compile | 0 | 0 |
| nose-compatibility | 1 | 0 (Nose retired, check retained) |
| collect-tests | 0 | 0 |
| tests | 1 | 0 |
| declared-test-workflow (`make test-nose`) | 2 | 0 |
| report-tests (original test) | 1 | 0 |

Counts: baseline 10 collected / 9 passed / 1 failed / 0 skipped / 0 errors; patched 10 / 10 / 0 / 0 / 0. Earlier profile v1 evidence is preserved separately and is not compared to v2.

The original report error was Jinja2 2.11.3 importing removed MarkupSafe `soft_unicode`; Nose imported removed Python `imp`. Both Jinja manifests were updated. Nose's actual Makefile invocation and README label were migrated, retaining original tests/ scope. Pydantic constraints remain aligned and public v2 APIs preserve the original validation contract.

## Provenance and limitations

Fresh repository analysis run `bf4f9872dba642c193624286baa7b501` cloned the actual target, executed a baseline and completed four real direct-Qwen batches. This demonstrates the existing analysis/proposal path, not correctness of every recommendation. The bounded fresh Qwen diagnostic review is in `docs/evidence/final-qwen-diagnosis.json`; incorrect report attribution and downgrade advice were explicitly rejected.

Fresh bounded actual Hermes inspection is in `docs/evidence/final-hermes-inspection.json`: official unmodified `git.db44c46`, MIT, local `veripatch-qwen3.5:4b-64k`. Actual tool execution, returned file content/hash and conversation tool messages are retained. Direct Qwen uses installed `qwen2.5-coder:7b`. No model changes/downloads occurred in finalization; only normal target dependency installation for verification.

The final approved exact edits are maintainer-assisted. The Pydantic alignment originated in historical direct-Qwen proposal `P-d3c6699c60`, preserved with its original timestamp. No maintainer changes are attributed to Hermes or presented as autonomous AI output. Hermes autonomous patch generation remains disabled.

Remaining observations: private/deprecated APIs, timeout defaults, charset handling, global Requests mutation, transitive-only certifi declaration and URL authority validation. LOCAL trusts target code; venvs are not security sandboxes. DigitalOcean is optional and unverified. See complete evidence/next actions in `docs/evidence/final-validation.json` and capsule.json.

## Reproduce

Unzip the capsule and follow `REPRODUCE.md`. Apply the approved diff only inside a fresh clone of the exact target commit. Use the current project's worker profile v2 on both baseline and patched copies. Preserve all original tests. Model outputs need not repeat; replay the recorded exact diff.
