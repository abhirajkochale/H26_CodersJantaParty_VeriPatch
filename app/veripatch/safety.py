import re
from pathlib import Path

EXCLUDED = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.aws', '.ssh', '.codex', '.agents'}

def safe_file(path):
    p = Path(path)
    return (not any(x in EXCLUDED for x in p.parts) and not any(x.startswith('.env') for x in p.parts)
            and not re.search(r'(?i)(credential|secret|token|password|\.pem$|\.key$|id_rsa|id_ed25519)', str(p)))

def repository_url(value):
    if not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?/?', value):
        raise ValueError('Use a public https://github.com/owner/repository URL without credentials or query strings')
    if any(part in {'.','..'} for part in value.split('/')): raise ValueError('Invalid repository path')
    return value.rstrip('/')
