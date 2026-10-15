# Attribution

## Actual Hermes integration

NousResearch Hermes Agent, MIT, unmodified official source pinned to `db44c46208f1b421b4ecb7e56bf9d68b0423906f` (`git.db44c46`): https://github.com/NousResearch/hermes-agent . Its license remains in the separate `.hermes-runtime/source/LICENSE` checkout. Documented AIAgent API and plugin registration provide the agent loop/tool execution. VeriPatch supplies the guarded tools, approval and verification/evidence workflow.

Qwen3.5-4B, Qwen team, Apache-2.0: https://huggingface.co/Qwen/Qwen3.5-4B . Local Ollama tag `qwen3.5:4b`, configured alias `veripatch-qwen3.5:4b-64k`; actual model digest and served context are retained with tool activity. Existing direct Qwen2.5-Coder functionality remains separately labeled.

## Final architecture and approved replay

Hermes is inspection/baseline only; autonomous patch generation is disabled. The approved Pydantic repair `Q-d3c6699c60` is an exact recovery of direct Ollama Qwen2.5-Coder 7B proposal `P-d3c6699c60` from local run `5f2114e6a2054299b50f3f8aaad0d4ab`. It is not Hermes-authored or a new inference. VeriPatch validated its target SHA, exact diff and preflight, recorded user approval, and ran fresh LOCAL verification. Historical model claims remain labeled hypotheses; the original “latest version” assertion is not adopted as fact.
