"""Bounded whole-repository inventory. Static observations are never execution claims."""
import ast
import hashlib
import re
import sys
import tomllib
from pathlib import Path
from packaging.requirements import Requirement, InvalidRequirement
from packaging.utils import canonicalize_name
from packaging.version import Version

EXCLUDED = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'build', 'dist', '.pytest_cache', '.ruff_cache', '.aws', '.ssh', '.codex', '.agents'}
SUPPORTED = {'.py', '.toml', '.txt', '.cfg', '.ini', '.yaml', '.yml', '.json', '.md', '.j2'}
ALIASES = {'yaml': 'pyyaml', 'dateutil': 'python-dateutil', 'PIL': 'pillow', 'bs4': 'beautifulsoup4', 'pkg_resources': 'setuptools'}

def safe_file(path):
    p = Path(path)
    return (not any(x in EXCLUDED for x in p.parts) and not any(x.startswith('.env') for x in p.parts)
            and not re.search(r'(?i)(credential|secret|token|password|\.pem$|\.key$|id_rsa|id_ed25519)', str(p)))

def compatible(constraints):
    """Find a concrete witness; prove simple interval conflicts; otherwise return unknown."""
    specs = [Requirement('x' + c).specifier for c in constraints]
    candidates = {Version(f'{i}.{j}.{k}') for i in range(4) for j in range(12) for k in (0, 1)}
    lower = None
    upper = None
    exact = []
    for spec in specs:
        for s in spec:
            try:
                v = Version(s.version)
            except Exception:
                continue
            release = list(v.release) + [0, 0]
            a, b, c = release[:3]
            candidates.update(Version(x) for x in (str(v), f'{a}.{b}.{c+1}', f'{a}.{b+1}.0', f'{a+1}.0.0'))
            if s.operator == '==': exact.append(v)
            if s.operator in ('>', '>='):
                bound = (v, s.operator == '>')
                lower = max(lower, bound) if lower else bound
            if s.operator in ('<', '<='):
                bound = (v, s.operator == '<')
                upper = min(upper, bound, key=lambda x: (x[0], not x[1])) if upper else bound
    if any(all(v in s for s in specs) for v in candidates): return 'compatible'
    if exact: return 'conflicting'
    if lower and upper and (lower[0] > upper[0] or (lower[0] == upper[0] and (lower[1] or upper[1]))): return 'conflicting'
    return 'unknown'

def inspect(root):
    root = Path(root)
    files, skipped, findings, imports, declarations = {}, [], [], [], []
    def finding(rule, title, path, line, snippet, detail, dependency=None):
        fid = 'F-' + hashlib.sha256(f'{rule}:{path}:{line}:{snippet}'.encode()).hexdigest()[:10]
        findings.append(dict(id=fid, rule=rule, title=title, dependency=dependency, severity='medium',
                             evidence_status='source_observed', repair_status='unresolved', detail=detail,
                             evidence=[dict(id='E-'+fid[2:], path=path, line=line, snippet=snippet, kind='source_observed')]))
    for p in sorted(root.rglob('*')):
        rel = str(p.relative_to(root))
        if any(part in EXCLUDED or part.endswith('.egg-info') for part in p.relative_to(root).parts): continue
        if p.is_symlink(): skipped.append(dict(path=rel, reason='symlink')); continue
        if not p.is_file(): continue
        if not safe_file(rel): skipped.append(dict(path=rel, reason='sensitive filename')); continue
        if p.stat().st_size > 160_000: skipped.append(dict(path=rel, reason='over 160 KB')); continue
        if p.suffix not in SUPPORTED and p.name not in {'Dockerfile', 'Makefile', 'LICENSE'}:
            skipped.append(dict(path=rel, reason='unsupported format')); continue
        try:
            content = p.read_text('utf-8')
            if '\x00' in content: raise ValueError('binary')
        except (UnicodeError, ValueError): skipped.append(dict(path=rel, reason='binary/non-UTF8')); continue
        if re.search(r'''(?im)(?:api[_-]?key|password|secret|token)\s*[=:]\s*["'](?:[^"'\n]{8,})["']|-----BEGIN [^-]*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9_]{16,}''', content):
            skipped.append(dict(path=rel, reason='potential credential content')); continue
        files[rel] = content
    def add_req(value, path, group):
        try:
            req = Requirement(value)
            declarations.append(dict(name=canonicalize_name(req.name), constraint=str(req.specifier), marker=str(req.marker) if req.marker else None,
                                     url=req.url, path=path, group=group, raw=value))
        except InvalidRequirement:
            finding('unparsed-dependency', 'Dependency declaration requires manual review', path, 1, value, 'Unsupported requirement syntax or include directive. No constraint conclusion made.')
    for path, source in files.items():
        if Path(path).name.startswith('requirements') and path.endswith('.txt'):
            for n, line in enumerate(source.splitlines(), 1):
                value = line.split(' #')[0].strip()
                if value and not value.startswith('#'): add_req(value, path, 'development' if 'dev' in path or 'test' in path else 'runtime')
        if path.endswith('.toml'):
            try:
                config = tomllib.loads(source)
                for value in config.get('project', {}).get('dependencies', []): add_req(value, path, 'runtime')
                for group, values in config.get('project', {}).get('optional-dependencies', {}).items():
                    for value in values: add_req(value, path, 'optional:'+group)
                for value in config.get('build-system', {}).get('requires', []): add_req(value, path, 'build')
            except Exception as e: finding('invalid-toml', 'Cannot parse TOML', path, 1, source[:200], str(e))
        if not path.endswith('.py'): continue
        try: tree = ast.parse(source)
        except SyntaxError as e:
            finding('invalid-python', 'Python syntax error', path, e.lineno or 1, e.text or '', str(e)); continue
        aliases = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    aliases[a.asname or a.name.split('.')[0]] = a.name
                    imports.append(dict(module=a.name, path=path, line=node.lineno))
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imports.append(dict(module=node.module, path=path, line=node.lineno))
                for a in node.names: aliases[a.asname or a.name] = node.module + '.' + a.name
        def fullname(node):
            if isinstance(node, ast.Name): return aliases.get(node.id, node.id)
            if isinstance(node, ast.Attribute): return fullname(node.value) + '.' + node.attr
            return ''
        for node in ast.walk(tree):
            snippet = ast.get_source_segment(source, node) or ''
            line = getattr(node, 'lineno', 1)
            if isinstance(node, ast.ImportFrom) and node.module and any(a.name.startswith('_') for a in node.names):
                finding('private-api', 'Private API import', path, line, snippet, 'Private symbols are outside the public compatibility contract; verify against the selected version.', node.module.split('.')[0])
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or '']
                for name in names:
                    if name.split('.')[0] in {'pkg_resources', 'imp', 'distutils'}:
                        finding('deprecated-module', 'Deprecated or removed module', path, line, snippet, 'Module has a deprecated or removed standard/distribution API; baseline execution establishes runtime impact.', ALIASES.get(name, name))
            if isinstance(node, ast.Call):
                name = fullname(node.func)
                if (name.startswith('requests.') or (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id in {'session', 'sess'})) and name.split('.')[-1] in {'get','post','put','delete','head','request','patch','options'}:
                    if not any(k.arg == 'timeout' or k.arg is None for k in node.keywords):
                        finding('http-timeout', 'HTTP call has no explicit timeout', path, line, snippet, 'This call has no timeout keyword. Indirect wrappers/defaults require review.', 'requests')
                if name in {'pydantic.validator', 'pydantic.root_validator'}:
                    finding('pydantic-legacy-api', 'Pydantic v1-style validator', path, line, snippet, 'Legacy validators need review if the effective environment selects Pydantic v2.', 'pydantic')
                if name.endswith('.decode') and any(isinstance(a, ast.Call) for a in node.args):
                    finding('dynamic-charset', 'Dynamic codec lookup can fail', path, line, snippet, 'Untrusted or detected encoding can cause LookupError. Inspect fallback handling and regression coverage.')
                if name.endswith('.startswith') and any(isinstance(a, ast.Tuple) and any(isinstance(x, ast.Constant) and str(x.value).startswith('http') for x in a.elts) for a in node.args):
                    finding('url-prefix-validation', 'URL validation checks only a prefix', path, line, snippet, 'A scheme prefix does not establish a valid host or authority; inspect URL parsing requirements.')
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(fullname(t).startswith('requests.') and fullname(t).endswith('.request') for t in targets):
                    finding('global-monkey-patch', 'Global HTTP behavior is replaced', path, line, snippet, 'Process-wide assignment changes Requests behavior for other callers; review scope and ordering.', 'requests')
    names = {d['name'] for d in declarations}
    local_modules = {Path(p).parts[0] for p in files} | {Path(p).stem for p in files if p.endswith('.py')}
    for imp in imports:
        top = imp['module'].split('.')[0]
        dep = canonicalize_name(ALIASES.get(top, top))
        if top not in sys.stdlib_module_names and top not in local_modules and dep not in names:
            finding('undeclared-import', 'Direct import has no matching declaration', imp['path'], imp['line'], imp['module'], 'Static module-to-distribution mapping is heuristic; transitive availability is not a direct declaration.', dep)
    deps = []
    for name in sorted(names):
        ds = [d for d in declarations if d['name'] == name]
        runtime = [d for d in ds if d['group'] == 'runtime' and not d['marker'] and not d['url']]
        result = compatible([d['constraint'] for d in runtime]) if runtime else 'unknown'
        if result == 'conflicting':
            for d in runtime:
                source = files[d['path']]
                line = next((i for i, l in enumerate(source.splitlines(), 1) if d['raw'] in l), 1)
                finding('dependency-conflict', 'Conflicting declarations: '+name, d['path'], line, d['raw'], 'No version can satisfy these unconditional runtime constraints: '+', '.join(x['constraint'] for x in runtime), name)
        if name == 'nose':
            for d in ds:
                finding('legacy-test-runner', 'Legacy test infrastructure needs Python 3.12 validation', d['path'], 1, d['raw'], 'Nose uses legacy import machinery in known releases; verify the installed runner on the actual Python version.', name)
        usage = [i for i in imports if canonicalize_name(ALIASES.get(i['module'].split('.')[0], i['module'].split('.')[0])) == name]
        deps.append(dict(name=name, declarations=ds, usage=usage, constraint_status=result, metadata_status='unknown: remote package metadata not queried',
                         finding_ids=[f['id'] for f in findings if f.get('dependency') == name], disposition='needs_review' if any(f.get('dependency') == name for f in findings) else 'no_static_finding'))
    return dict(files=files, dependencies=deps, findings=findings, coverage=dict(inspected_files=len(files), python_files=sum(p.endswith('.py') for p in files), skipped=skipped,
                excluded_directories=sorted(EXCLUDED)+['*.egg-info'],
                limitations=['Static rules cover Python AST, PEP 508 requirements and PEP 621 TOML. Other formats are inventoried as text only.',
                             'Dynamic imports, arbitrary bugs, conditional constraints and distribution aliases may need manual review.',
                             'No package-age inference or exhaustive bug discovery claim. Metadata unavailable is unknown.']))
