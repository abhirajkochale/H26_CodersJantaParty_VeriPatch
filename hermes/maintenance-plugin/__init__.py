"""Trusted Hermes plugin. All authority stays in the application process."""
import json
import os
import sys

def register(ctx):
    def bridge(name):
        def handle(args, **kwargs):
            sys.__stdout__.write(json.dumps({'type':'tool_request','tool':name,'arguments':args})+'\n')
            sys.__stdout__.flush()
            reply=json.loads(sys.stdin.readline())
            return json.dumps(reply)
        return handle
    schemas={
        'inspect_repository': ('Inventory target files, dependency declarations, findings and current verification. Start here.', {'type':'object','properties':{},'additionalProperties':False}),
        'read_repository_file': ('Read an inventoried repository file before proposing edits. Returns actual contents and SHA256.', {'type':'object','properties':{'path':{'type':'string'}},'required':['path'],'additionalProperties':False}),
        'verify_repository': ('Execute the fixed isolated LOCAL profile on the current copy. No shell commands accepted. Baseline is cached; patched execution requires prior human approval.', {'type':'object','properties':{},'additionalProperties':False}),
    }
    for name,(description,parameters) in schemas.items():
        ctx.register_tool(name=name,toolset='veripatch_maintenance',schema={'name':name,'description':description,'parameters':parameters},handler=bridge(name))
