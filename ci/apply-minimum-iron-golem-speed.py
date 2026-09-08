from pathlib import Path
import json
import re

root = Path('project/src/main/resources/data/golems/golems/golem')
changed = []
for p in sorted(root.glob('*.json')):
    try:
        data = json.loads(p.read_text())
    except Exception:
        continue
    attrs = data.get('attributes')
    if not isinstance(attrs, dict) or 'speed' not in attrs:
        continue
    speed = float(attrs['speed'])
    if speed >= 0.25:
        continue
    text = p.read_text()
    pattern = re.compile(r'("speed"\s*:\s*)(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)')
    m = pattern.search(text)
    if not m:
        raise SystemExit(f'Could not locate speed literal in {p}')
    text = text[:m.start(2)] + '0.25' + text[m.end(2):]
    p.write_text(text)
    changed.append((p.name, speed))

expected = {'moss.json','gold.json','raw_gold.json','raw_copper.json','raw_iron.json','obsidian.json','crying_obsidian.json','mud.json','terracotta.json'}
actual = {name for name, _ in changed}
if actual != expected:
    raise SystemExit(f'Unexpected speed-floor set. expected={sorted(expected)} actual={sorted(actual)}')
print('Raised sub-0.25 speed definitions:', ', '.join(f'{n}:{v}->0.25' for n,v in changed))
