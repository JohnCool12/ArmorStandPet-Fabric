from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/data/behavior/util/TargetedMobEffects.java')
s = p.read_text()

old_loop = '''\t\t\t\tfor (LivingEntity target : targets) {\n\t\t\t\t\tif (excludeBystanderPlayers && target instanceof Player && target != directAttackTarget) {\n\t\t\t\t\t\tcontinue;\n\t\t\t\t\t}\n\t\t\t\t\tcopyEffects(target, rolls, effects);\n\t\t\t\t}\n'''
new_loop = '''\t\t\t\tfor (LivingEntity target : targets) {\n\t\t\t\t\tif (!shouldApplyToAreaTarget(target, directAttackTarget)) {\n\t\t\t\t\t\tcontinue;\n\t\t\t\t\t}\n\t\t\t\t\tcopyEffects(target, rolls, effects);\n\t\t\t\t}\n'''
if s.count(old_loop) != 1:
    raise SystemExit(f'Expected inline player-bystander filter once, found {s.count(old_loop)}')
s = s.replace(old_loop, new_loop, 1)

anchor = '''\tpublic List<MobEffectInstance> getEffects() {\n\t\treturn effects;\n\t}\n\n\t/**\n\t * Applies the effects based on the target\n'''
replacement = '''\tpublic List<MobEffectInstance> getEffects() {\n\t\treturn effects;\n\t}\n\n\t/**\n\t * Returns whether an AREA effect should be applied to this candidate. When the\n\t * opt-in bystander-player exemption is enabled, players are skipped unless the\n\t * candidate is the exact entity directly struck by the attack that triggered the\n\t * effect. Non-player living entities retain the original area-effect behavior.\n\t */\n\tpublic boolean shouldApplyToAreaTarget(LivingEntity target, Entity directAttackTarget) {\n\t\treturn !excludeBystanderPlayers || !(target instanceof Player) || target == directAttackTarget;\n\t}\n\n\t/**\n\t * Applies the effects based on the target\n'''
if s.count(anchor) != 1:
    raise SystemExit(f'Expected getter/apply anchor once, found {s.count(anchor)}')
s = s.replace(anchor, replacement, 1)

if s.count('shouldApplyToAreaTarget(target, directAttackTarget)') != 1:
    raise SystemExit('AREA loop is not using the explicit predicate exactly once')
if s.count('public boolean shouldApplyToAreaTarget') != 1:
    raise SystemExit('Target predicate method missing or duplicated')

p.write_text(s)
print('Refined Sculk player-bystander filter into explicit runtime predicate used by AREA loop.')
