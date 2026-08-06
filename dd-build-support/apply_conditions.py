#!/usr/bin/env python3
import json
import pathlib
import sys

if len(sys.argv) != 3:
    raise SystemExit('usage: apply_conditions.py <workspace> <manifest>')
workspace = pathlib.Path(sys.argv[1])
manifest = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8'))
missing=[]
for rel, conditions in manifest.items():
    path = workspace / rel
    if not path.exists():
        missing.append(rel)
        continue
    data = json.loads(path.read_text(encoding='utf-8'))
    data.pop('neoforge:conditions', None)
    data.pop('forge:conditions', None)
    data['fabric:load_conditions'] = conditions
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
if missing:
    raise SystemExit(f'{len(missing)} compatibility resource(s) missing; first: {missing[0]}')
print(f'Applied Fabric load conditions to {len(manifest)} resources')
