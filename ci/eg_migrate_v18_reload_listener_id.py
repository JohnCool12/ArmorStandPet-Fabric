#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(sys.argv[1] if len(sys.argv)>1 else 'work').resolve()
p=ROOT/'src/main/java/com/mcmoddev/golems/client/EGClientEvents.java'
s=p.read_text()
s=s.replace('event.addListener(new SimplePreparableReloadListener<Void>() {', 'event.addListener(net.minecraft.resources.Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "dynamic_textures"), new SimplePreparableReloadListener<Void>() {')
p.write_text(s)
print('Applied explicit 26.1 client reload listener id pass 18')
