#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(sys.argv[1] if len(sys.argv)>1 else 'work').resolve()
p=ROOT/'src/main/java/com/mcmoddev/golems/item/SpawnGolemItem.java'
s=p.read_text()
ending='\n\t}\n\t}\n}'
if s.endswith(ending):
    s=s[:-len(ending)]+'\n\t}\n}'
else:
    raise SystemExit('Unexpected SpawnGolemItem EOF; refusing broad rewrite')
p.write_text(s)
print('Applied exact SpawnGolemItem EOF repair pass 6')
