import hashlib
import json
import os
from pathlib import Path

def register(ctx):
    def read(args,**kwargs):
        root=Path(os.environ['VP_PROBE_ROOT']).resolve()
        path=Path(args.get('path',''))
        try:
            if path.is_absolute() or '..' in path.parts: raise ValueError('Unsafe relative path')
            target=root/path
            if target.is_symlink() or not target.resolve().is_relative_to(root): raise ValueError('Symlink escape')
            source=target.read_text()
            result=dict(path=str(path),content=source[:4000],sha256=hashlib.sha256(source.encode()).hexdigest(),truncated=len(source)>4000)
        except Exception as e: result={'error':str(e)}
        with Path(os.environ['VP_PROBE_EVENTS']).open('a') as f:
            f.write(json.dumps(dict(event='handler_executed',tool='repository_read',arguments=args,result=result))+'\n')
        return json.dumps(result)
    ctx.register_tool(name='repository_read',toolset='veripatch_probe',schema=dict(name='repository_read',description='Read an actual UTF-8 file in the target repository. Returns contents and SHA-256.',parameters=dict(type='object',properties={'path':{'type':'string'}},required=['path'],additionalProperties=False)),handler=read)
