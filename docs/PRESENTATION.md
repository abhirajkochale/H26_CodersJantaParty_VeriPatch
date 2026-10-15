# Presentation and reproducible demo

## 1. Team, track and problem
CodersJantaParty · VeriPatch · Track 2, Maintenance Agent Skill. Repository maintenance involves interacting constraints, brittle runtime behavior and difficult dependency exits. A chatbot explanation alone does not establish that a repair works.

## 2. Solution and workflow
Public repository → exact commit → whole supported-file inventory → executed baseline → runtime local Qwen root-cause/patch proposals → readable diff → selected repair in a separate clone → equivalent verification → Dependency Exit Capsule. Evidence and repair status remain separate throughout.

## 3. Technical approach
React/TypeScript/Vite and Python 3.12/FastAPI. AST and packaging/TOML rules create reproducible observations. Qwen2.5-Coder 7B via local Ollama provides the AI reasoning and edits with structured output. A fixed SSH worker executes real installation and tests in disposable Docker containers on DigitalOcean. Atomic state and a cross-process lock prevent conflicting operations. Protected tests, exact-match edits and collection comparisons make repair claims inspectable.

## 4. Feasibility and limitations
Runs locally with an installed 7B quantized model; evidence batches fit a 16 GB Mac. DigitalOcean needs an existing configured Droplet; no billable provisioning is automatic. The supported profile focuses on Python/pytest. Model proposals may be invalid or incomplete; visible failures remain in the capsule. LOCAL venv execution is for trusted code, not a security sandbox. No exhaustive bug-discovery claim.

## 5. Impact and measurable benefits
Show actual files/dependencies inventoried, detected issues accounted for, model batches, baseline/patched test counts, collection preservation, command durations and unresolved issues from the live run. Do not promise invented time savings or success percentages. Reusable capsules make dependency decisions and handoffs reproducible. Judge original functionality through provenance, guarded exact edits, provider identity, equivalent checks and issue-specific repair status.

## 6. References
Original LinkWatch and preserved MIT license; Qwen model card and Apache-2.0 license; Ollama structured chat interface; DigitalOcean Droplets; Python AST, packaging, TOML, pytest; React, Vite and FastAPI. See ATTRIBUTION.md and README links.

## Demo sequence

1. Start Ollama and run `model-smoke`; show real validated output and model tag.
2. Start VeriPatch and open http://127.0.0.1:8000.
3. Check DigitalOcean worker connection. If missing, show the exact unconfigured state and identify the mandatory demo gap honestly.
4. Paste https://github.com/rishrek/LinkWatch. Choose DIGITALOCEAN when configured, otherwise explicitly LOCAL. Analyze; show backend stages and exact commit.
5. Inspect dependencies and source findings. Open an execution failure and its real log. Distinguish static observation from verified runtime failure.
6. Open AI & patches. Read Qwen's root cause, uncertainty and concrete diff. Use Plan integrated repair to connect runtime/dependency failures when individual alternatives are incomplete. Choose a valid reviewed proposal and Apply & verify. Failed proposals are useful honest evidence, not hidden.
7. Compare collected/pass/fail/skip counts and command scope. Show unresolved findings after verification.
8. Download the capsule; inspect capsule.json, REPORT.md, baseline/AI/verification separation, patch and command logs.
9. State actual results from this run and remaining limitations. Do not call LOCAL results DigitalOcean.

## Fallback recording checklist

- Record an actual successful model smoke test, exact source commit and baseline execution.
- Include timestamp, provider label and command results on screen.
- Capture a real AI diff and actual apply/verify result, including failures.
- Show DigitalOcean metadata identity and remote executed test logs if access exists.
- Download and inspect the generated ZIP.
- Keep a copied real capsule and recording outside the source tree; never substitute fixture results for a live run.
- If cloud access fails at judging time, present the earlier genuine recording with its timestamp and explain that live cloud access is unavailable. Without a genuine cloud recording, say the mandatory cloud demonstration is pending.
