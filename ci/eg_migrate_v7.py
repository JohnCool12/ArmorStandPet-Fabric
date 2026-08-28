#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else 'work').resolve()
p = ROOT / 'src/main/java/com/mcmoddev/golems/item/SpawnGolemItem.java'
s = p.read_text()
lines = s.splitlines()

# The previous migration accidentally leaves one duplicate class-closing brace:
# ... spawnParticles method closes, then two one-tab braces, then the class brace.
# Remove exactly the second-to-last one-tab brace and nothing else.
if len(lines) >= 3 and lines[-3:] == ['\t}', '\t}', '}']:
    del lines[-2]
else:
    raise SystemExit('Unexpected SpawnGolemItem EOF shape: ' + repr(lines[-6:]))

p.write_text('\n'.join(lines) + '\n')
print('Applied exact SpawnGolemItem duplicate-brace repair pass 7')
