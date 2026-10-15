import fcntl
import json
import os
from pathlib import Path
import threading
import uuid

class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.lock = threading.Lock()
    def directory(self, id):
        if not __import__('re').fullmatch('[0-9a-f]{32}',id): raise ValueError('Invalid run ID')
        return self.root/id
    def save(self, run):
        folder = self.directory(run['id']); folder.mkdir(exist_ok=True)
        temp = folder/('state-'+uuid.uuid4().hex+'.tmp')
        with temp.open('w') as f:
            json.dump(run,f,indent=2); f.flush(); os.fsync(f.fileno())
        os.replace(temp,folder/'run.json')
    def get(self,id): return json.loads((self.directory(id)/'run.json').read_text())
    def list(self):
        return sorted([json.loads(p.read_text()) for p in self.root.glob('*/run.json')],key=lambda r:r['created_at'],reverse=True)
    def reserve(self):
        if not self.lock.acquire(blocking=False): raise RuntimeError('Another operation is running')
        handle = (self.root/'operation.lock').open('a')
        try: fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            handle.close(); self.lock.release(); raise RuntimeError('Another coordinator owns the operation lock')
        def release():
            fcntl.flock(handle,fcntl.LOCK_UN); handle.close(); self.lock.release()
        return release
