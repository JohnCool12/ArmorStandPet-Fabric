#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(sys.argv[1] if len(sys.argv)>1 else 'work').resolve()
SRC=ROOT/'src/main/java'

g=SRC/'com/mcmoddev/golems/entity/GolemBase.java'
s=g.read_text()
# Pass 3 replaced the method header/body but its non-greedy regex left the original
# final return + method brace immediately after the new getLootTable implementation.
stray='\n\t\treturn ResourceKey.create(net.minecraft.core.registries.Registries.LOOT_TABLE, oContainer.get().getLootTable());\n\t}'
if stray in s:
    s=s.replace(stray,'',1)
# Pass 3 save-method migration can likewise leave one duplicate method-closing brace.
# Normalize only the known double brace immediately before the SPAWN DATA marker.
s=s.replace('\n\t}\n\t}\n\n\t//// SPAWN DATA ////','\n\t}\n\n\t//// SPAWN DATA ////')
g.write_text(s)

p=SRC/'com/mcmoddev/golems/item/SpawnGolemItem.java'
s=p.read_text()
# Tooltip migration consumed the inner if-body but left the method closing brace.
# At EOF this appears as two class-level closes; remove only the penultimate one.
ending='\n\t}\n}'
if s.endswith(ending):
    s=s[:-len(ending)]+'\n}'
p.write_text(s)

print('Applied parser repair pass 4')
