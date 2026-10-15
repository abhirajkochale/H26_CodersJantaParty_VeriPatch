"""Exact, transactional edits; no model commands and no target-test changes."""
import difflib
import ast
import hashlib
import json
import re
import tomllib
from pathlib import Path, PurePosixPath
from .safety import safe_file

ALLOWED = {'.py', '.toml', '.txt', '.cfg', '.ini', '.json', '.yaml', '.yml', '.j2'}

def validate_edits(root, edits):
    root = Path(root).resolve()
    changed = {}
    for edit in edits:
        path = edit['path']
        p = PurePosixPath(path)
        if not path or p.is_absolute() or '..' in p.parts or '\\' in path or any(x.startswith('.') for x in p.parts):
            raise ValueError('Unsafe patch path: '+path)
        if not safe_file(path) or p.suffix not in ALLOWED or any('test' in x.lower() for x in p.parts):
            raise ValueError('Protected or unsupported file: '+path)
        target = root / path
        if any(x.is_symlink() for x in [target, *target.parents]) or not target.resolve().is_relative_to(root):
            raise ValueError('Symlink escape rejected')
        if not target.is_file(): raise ValueError('Edits must target an existing file')
        text = changed.get(path, target.read_text())
        before, after = edit['before'], edit['after']
        if not before or before == after or text.count(before) != 1:
            raise ValueError('Patch conflict: before must match exactly once in '+path)
        updated = text.replace(before, after, 1)
        if p.suffix == '.py':
            try: ast.parse(updated)
            except SyntaxError as e: raise ValueError('Patch produces invalid Python: '+str(e)) from e
        if re.search(r'(?:pytest\.(?:skip|exit)|pytest\.mark\.skip|unittest\.skip|--ignore|--deselect)', after) and not re.search(r'(?:pytest\.(?:skip|exit)|pytest\.mark\.skip|unittest\.skip|--ignore|--deselect)', before):
            raise ValueError('Edits may not suppress verification')
        if p.name in {'pytest.ini', 'tox.ini', 'setup.cfg'}:
            raise ValueError('Protected test configuration')
        if p.name == 'pyproject.toml':
            old_config = tomllib.loads(text).get('tool', {}).get('pytest', {})
            new_config = tomllib.loads(updated).get('tool', {}).get('pytest', {})
            if old_config != new_config: raise ValueError('Protected pytest configuration changed')
        changed[path] = updated
    if not changed: raise ValueError('Proposal has no edits')
    return changed

def diff_edits(root, edits):
    changed = validate_edits(root, edits)
    return ''.join(''.join(difflib.unified_diff((Path(root)/p).read_text().splitlines(True), s.splitlines(True), fromfile='a/'+p, tofile='b/'+p)) for p,s in changed.items())

def apply_edits(root, edits):
    changed = validate_edits(root, edits)
    for path, source in changed.items(): (Path(root)/path).write_text(source)

def patch_hash(edits):
    return hashlib.sha256(json.dumps(edits, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
