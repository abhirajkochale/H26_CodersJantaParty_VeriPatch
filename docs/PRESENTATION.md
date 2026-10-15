# VeriPatch presentation

CodersJantaParty · Track 2: repository maintenance with inspectable evidence.

The working workflow is direct-Qwen proposal → exact guarded diff → human approval → fixed isolated LOCAL verification → reusable Dependency Exit Capsule. The actual NousResearch Hermes Agent contributes separate repository inspection and baseline-verification tools. Its failed autonomous generation evidence is retained; patch generation is disabled rather than relabeled as working.

Our contribution is the guarded maintenance boundary, provenance, protected-test comparisons, individual issue status and capsule handoff. Hermes provides an existing open-source agent loop; Qwen/Ollama provide local inference. We did not build or train those systems.

Demonstrate the approved Pydantic conflict repair, pip check exit 1 → 0, unchanged original tests (10 collected, 9 pass / 1 fail / 0 skip), and remaining Nose/report failures. Do not claim a fully repaired repository or DigitalOcean execution.

Follow [HERMES_DEMO.md](HERMES_DEMO.md) for the short script, exact target commit, authorship, capsule and reproduction instructions.
