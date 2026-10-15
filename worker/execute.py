#!/usr/bin/env python3
"""Fixed Python 3.12 verification profile. Executed inside Docker or explicit trusted LOCAL mode."""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid
import resource

VERSION = '1'

def redact(text):
    text = re.sub(r'(?i)((?:password|secret|token|api[_-]?key)\s*[=:]\s*)[^\s,;]+', r'\1[REDACTED]', text)
    return re.sub(r'gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]{16,}', '[REDACTED]', text)

def command(name, argv, cwd, env, timeout=180):
    started = time.monotonic()
    out = Path(env['HOME']).parent / (name+'.stdout.log')
    err = Path(env['HOME']).parent / (name+'.stderr.log')
    timed_out = False
    with out.open('w') as stdout, err.open('w') as stderr:
        try:
            def limits():
                resource.setrlimit(resource.RLIMIT_FSIZE, (16_000_000, 16_000_000))
                resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr, start_new_session=True, preexec_fn=limits)
            try: code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                code = 124
            finally:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
        except OSError as e:
            code = 127
            stderr.write(str(e))
    # Bound persisted logs and explicitly report truncation.
    def read(p):
        with p.open('rb') as f: data = f.read(2_000_001)
        return redact(data[:2_000_000].decode('utf-8', 'replace')), len(data)>2_000_000
    stdout, a = read(out)
    stderr, b = read(err)
    out.write_text(stdout); err.write_text(stderr)
    return dict(name=name, argv=argv, cwd=str(cwd), runtime=sys.version, exit_code=code, duration_seconds=round(time.monotonic()-started, 2),
                stdout=stdout, stderr=stderr, timed_out=timed_out, logs_truncated=a or b)

def execute(root):
    root = Path(root).resolve()
    if sys.version_info[:2] != (3, 12): raise RuntimeError('Verification requires Python 3.12')
    work = root.parent / ('execution-'+uuid.uuid4().hex)
    work.mkdir()
    env = {'PATH':os.environ.get('PATH','/usr/local/bin:/usr/bin:/bin'), 'HOME':str(work / 'home'),
           'PYTHONUNBUFFERED':'1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1', 'PIP_DISABLE_PIP_VERSION_CHECK':'1', 'PIP_NO_INPUT':'1'}
    Path(env['HOME']).mkdir(exist_ok=True)
    venv = work / 'target-env'
    commands = []
    def run(name, args, timeout=180):
        r = command(name,args,root,env,timeout); commands.append(r); return r
    run('create-env', [sys.executable, '-m','venv',str(venv)])
    python = str(venv / 'bin/python')
    run('tooling', [python,'-m','pip','install','pytest==8.3.5'])
    reqs = [p.name for p in sorted(root.glob('requirements*.txt')) if p.is_file() and not p.is_symlink()]
    if reqs:
        args = [python,'-m','pip','install']
        for p in reqs: args.extend(['-r',p])
        run('install-requirements',args)
    if (root/'pyproject.toml').is_file() or (root/'setup.py').is_file():
        run('install-project', [python,'-m','pip','install','--no-deps','.'])
    run('dependency-check',[python,'-m','pip','check'])
    run('resolved-packages',[python,'-m','pip','list','--format=json'])
    run('compile',[python,'-m','compileall','-q','.'],60)
    run('nose-compatibility',[python,'-c',"import importlib.util; spec=importlib.util.find_spec('nose'); print('nose absent: no installed legacy runner' if spec is None else 'nose installed: importing for compatibility'); exec('import nose; print(nose.__version__)') if spec else None"],30)
    plugin = work/'vp_probe.py'
    plugin.write_text('''import json, os
from pathlib import Path
counts = {"collected": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0}
def pytest_collection_finish(session): counts["collected"] = len(session.items)
def pytest_runtest_logreport(report):
    if report.when == "call" or report.skipped:
        key = "passed" if report.passed else "skipped" if report.skipped else "failed"
        counts[key] += 1
    elif report.failed: counts["errors"] += 1
def pytest_collectreport(report):
    if report.failed: counts["errors"] += 1
def pytest_sessionfinish(session, exitstatus):
    Path(os.environ["VP_COUNTS"]).write_text(json.dumps(counts))
''')
    env['PYTHONPATH'] = str(work)
    env['VP_COUNTS'] = str(work/'counts.json')
    run('collect-tests',[python,'-m','pytest','--collect-only','-q','-p','vp_probe'],120)
    run('tests',[python,'-m','pytest','-q','-ra','-p','vp_probe'],120)
    counts = json.loads(Path(env['VP_COUNTS']).read_text()) if Path(env['VP_COUNTS']).exists() else None
    return dict(worker_version=VERSION, profile='python312-requirements-project-nodeps-pytest-v1', runtime=sys.version,
                commands=commands, counts=counts, success=all(x['exit_code']==0 for x in commands),
                limitations=['One combined requirements environment; project installed without dependency resolution; pip check records metadata mismatch.',
                             'No application-specific network/service integration beyond existing tests.', 'Target code and test output are untrusted. Logs redacted and capped at 2 MB per stream.'])

if __name__ == '__main__':
    try: print(json.dumps(execute(sys.argv[1])))
    except Exception as e:
        print(json.dumps(dict(error=str(e),worker_version=VERSION))); sys.exit(1)
