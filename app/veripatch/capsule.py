"""Allowlisted artifacts only: never include repository files, environments or configuration secrets."""
import copy
import json
from pathlib import Path
import re
import zipfile


def scrub(value):
    if isinstance(value, dict): return {k:scrub(v) for k,v in value.items() if k not in {'files','base_url'}}
    if isinstance(value, list): return [scrub(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r'(?i)((?:password|secret|token|api[_-]?key)\s*[=:]\s*)[^\s,;]+',r'\1[REDACTED]',value)
        value = re.sub(r'gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]{16,}','[REDACTED]',value)
        value = re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----','[REDACTED PRIVATE KEY]',value,flags=re.S)
        return value
    return value

def export(run, destination):
    clean = scrub(copy.deepcopy(run))
    report = ['# VeriPatch · Dependency Exit Capsule',f"Repository: {clean['url']}",f"Commit: {clean.get('commit','unknown')}",f"Analysis state: {clean['status']}",
              '\nA completed analysis is not a successfully repaired repository.', '\n## Coverage',json.dumps(clean.get('coverage',{}),indent=2),'\n## Maintenance findings']
    for f in clean.get('findings',[]):
        report += [f"### {f['id']} · {f['title']}", f"Evidence: {f['evidence_status']} · Repair: {f['repair_status']}",f['detail'],json.dumps(f['evidence'],indent=2)]
    report += ['\n## Dependency inventory',json.dumps(clean.get('dependencies',[]),indent=2),'\n## AI recommendations (hypotheses)',json.dumps(clean.get('ai',[]),indent=2),
               '\n## Verification',json.dumps(clean.get('comparison',{}),indent=2),'\n## Errors and unresolved concerns',json.dumps(clean.get('errors',[]),indent=2)]
    for phase in ['baseline','verification']:
        result=clean.get(phase,{})
        report += ['\n## Executed '+phase, 'Provider: '+str(result.get('provider','not executed')), 'Counts: `'+json.dumps(result.get('counts'))+'`', 'Profile: `'+str(result.get('profile','unknown'))+'`']
        if result.get('error'): report.append('Execution error: '+result['error'])
        report += ['| Command | Exit | Seconds | Timeout |', '|---|---:|---:|---|']
        for c in result.get('commands',[]): report.append(f"| {c['name']} | {c.get('exit_code','unknown')} | {c.get('duration_seconds','unknown')} | {c.get('timed_out','unknown')} |")
    report += ['\n## Authorship and retained evidence', 'Repair engine: '+str(clean.get('repair_engine',clean.get('engine','DIRECT'))), 'Inspection engine: '+str(clean.get('inspection_engine','static inventory')), 'Hermes records retain their original timestamps. Historical Qwen responses are not new inference.', json.dumps([{k:p.get(k) for k in ['id','authored_by','status','provenance']} for p in clean.get('proposals',[])],indent=2)]
    report += ['\n## Retained Hermes activity (original timestamps)',json.dumps(clean.get('hermes',{}).get('identity',{}),indent=2), '\n## Remaining limitations',json.dumps(clean.get('limitations',[]),indent=2)]
    applied=clean.get('applied_proposal_id','PROPOSAL_ID')
    reproduction = f'''# Reproduce
Exact public source: {clean['url']}
Commit: {clean.get('commit','unknown')}

1. Start VeriPatch with Python 3.12 using the project README. The default repair engine is direct Qwen2.5-Coder 7B through local Ollama. Optional Hermes inspection uses its separate pinned runtime and veripatch-qwen3.5:4b-64k with actual 65536 context; see docs/HERMES_SETUP.md. Hermes identity, model digest, real tool messages/results, approvals and all attempts are in hermes/activity.json and verification/attempts.json.
2. Analyze this URL and confirm the recorded commit (the default UI analyzes current HEAD).
3. For exact reproduction, use `git clone`, `git checkout {clean.get('commit','COMMIT')}` and the fixed worker profile documented in docs/ARCHITECTURE.md.
4. Review the proposed exact-match edits and their uncertainty. Applied edit records appear in capsule.json.
5. Run the same verification profile on baseline and patched copies. Compare collection and skip counts.

Provider: {clean.get('provider','unknown')}. LOCAL virtual environments are not security sandboxes.
DigitalOcean requires a configured existing Droplet. See docs/DIGITALOCEAN.md.
Exact LOCAL execution replay from the VeriPatch project root (executes trusted target code):

```bash
git clone {clean['url']} /private/tmp/veripatch-reproduce-baseline
git -C /private/tmp/veripatch-reproduce-baseline checkout --detach {clean.get('commit','COMMIT')}
app/.venv/bin/python worker/execute.py /private/tmp/veripatch-reproduce-baseline > /private/tmp/baseline.json
git clone --no-hardlinks /private/tmp/veripatch-reproduce-baseline /private/tmp/veripatch-reproduce-patched
# Unzip this capsule, then replace /absolute/path/to/capsule below:
git -C /private/tmp/veripatch-reproduce-patched apply /absolute/path/to/capsule/patches/{applied}.diff
app/.venv/bin/python worker/execute.py /private/tmp/veripatch-reproduce-patched > /private/tmp/patched.json
```

Use fresh destination directories. These direct worker invocations are LOCAL; they do not prove DigitalOcean execution. To reproduce cloud execution, configure the SSH worker and submit the recorded URL, commit, applied_edits and canonical patch hash through the fixed protocol described in docs/DIGITALOCEAN.md.

Installations are not fully locked transitively; resolved package versions and runtime are in logs. AI output may differ across repeated calls; replay the recorded diff to reproduce the applied source changes.
The capsule records observations, AI hypotheses, and executed results separately; no arbitrary model commands are executed.
'''
    if not clean.get('applied_proposal_id'):
        start=reproduction.index('git clone --no-hardlinks')
        end=reproduction.index('```',start)
        reproduction=reproduction[:start]+reproduction[end:]
        reproduction+='\nNo patch was approved or applied in this run. Patched verification was NOT executed. Any proposal diffs in this capsule are unapproved hypotheses, not reproduction-ready repairs. Inspect their status and tool validation errors. Reproduce the baseline only; do not interpret missing patched results as passing.\n'
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('capsule.json',json.dumps(clean,indent=2))
        z.writestr('REPORT.md','\n\n'.join(report))
        z.writestr('REPRODUCE.md',reproduction)
        z.writestr('hermes/activity.json',json.dumps(clean.get('hermes',{}),indent=2))
        z.writestr('hermes/approvals.json',json.dumps(clean.get('approvals',[]),indent=2))
        z.writestr('verification/attempts.json',json.dumps(clean.get('verification_attempts',[]),indent=2))
        if clean.get('applied_diff'):z.writestr('patches/'+applied+'.diff',clean['applied_diff'])
        z.writestr('baseline/result.json',json.dumps(clean.get('baseline',{}),indent=2))
        z.writestr('ai/responses.json',json.dumps(clean.get('ai',[]),indent=2))
        z.writestr('verification/result.json',json.dumps(clean.get('verification',{'status':'not_executed','reason':'No approved patch verification recorded'}),indent=2))
        for p in clean.get('proposals',[]):
            if p['id']==applied and clean.get('applied_diff'):continue
            z.writestr('patches/'+p['id']+'.diff',p.get('diff',''))
        for phase in ['baseline','verification']:
            for i,c in enumerate(clean.get(phase,{}).get('commands',[])):
                z.writestr(f'{phase}/logs/{i:02d}-{c["name"]}.stdout.log',c['stdout'])
                z.writestr(f'{phase}/logs/{i:02d}-{c["name"]}.stderr.log',c['stderr'])
    return Path(destination)
