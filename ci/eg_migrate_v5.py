#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(sys.argv[1] if len(sys.argv)>1 else 'work').resolve()
p=ROOT/'src/main/java/com/mcmoddev/golems/item/SpawnGolemItem.java'
s=p.read_text()
# Generated tail after the tooltip method removal is: method-close, stray-close, class-close.
s=s.replace('\n\t}\n\t\t}\n}', '\n\t}\n}')
p.write_text(s)
print('Applied final parser repair pass 5')
