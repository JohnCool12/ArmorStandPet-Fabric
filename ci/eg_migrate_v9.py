#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else 'work').resolve()
p = ROOT / 'src/main/java/com/mcmoddev/golems/data/behavior/AbstractShootBehavior.java'
s = p.read_text()
old = '''\t\t\tfor (Entity e : mob.level().getEntities(mob, aabb)) {\n\t\t\t\tif (!mob.canAttackType(e.getType())) {\n\t\t\t\t\treturn false;\n\t\t\t\t}\n\t\t\t}\n'''
new = '''\t\t\tfor (Entity e : mob.level().getEntities(mob, aabb)) {\n\t\t\t\tif (e instanceof net.minecraft.world.entity.LivingEntity living && !mob.canAttack(living)) {\n\t\t\t\t\treturn false;\n\t\t\t\t}\n\t\t\t}\n'''
if old not in s:
    raise SystemExit('Unexpected AbstractShootBehavior attackability block')
p.write_text(s.replace(old, new))
print('Applied final 26.1.2 ranged-path attackability migration pass 9')
