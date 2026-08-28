#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else 'work').resolve()
p = ROOT / 'src/main/java/com/mcmoddev/golems/entity/GolemBase.java'
s = p.read_text()
old = '''\t@Override\n\tpublic Optional<ResourceKey<net.minecraft.world.level.storage.loot.LootTable>> getLootTable() {\n\t\tfinal Optional<GolemContainer> oContainer = getContainer();\n\t\tif (oContainer.isEmpty()) return super.getLootTable();\n\t\treturn Optional.of(ResourceKey.create(net.minecraft.core.registries.Registries.LOOT_TABLE, oContainer.get().getLootTable()));\n\t}\n'''
new = '''\t@Override\n\tpublic Optional<ResourceKey<net.minecraft.world.level.storage.loot.LootTable>> getLootTable() {\n\t\tfinal Optional<GolemContainer> oContainer = getContainer();\n\t\tif (oContainer.isEmpty()) {\n\t\t\treturn super.getLootTable();\n\t\t}\n\t\treturn Optional.of(ResourceKey.create(net.minecraft.core.registries.Registries.LOOT_TABLE, oContainer.get().getLootTable()));\n\t}\n'''
if old not in s:
    raise SystemExit('Unexpected compact GolemBase loot override')
p.write_text(s.replace(old, new))
print('Normalized compact GolemBase loot override for semantic pass 8')
