from pathlib import Path

root = Path('project')
shoot_path = root / 'src/main/java/com/mcmoddev/golems/data/behavior/ShootArrowsBehavior.java'
text = shoot_path.read_text()

# Add a single authoritative instantaneous combat-mode test. The old 3.5-block
# trigger radius decides when melee may be considered, while Minecraft's own
# melee-range and sensing checks decide whether a real melee connection is possible.
anchor = '''\tprivate double getPreferredMaximumRange(final IExtraGolem entity) {\n'''
helper = '''\tprivate boolean shouldUseMeleeNow(final IExtraGolem entity, final LivingEntity target) {\n\t\tif (target == null || !target.isAlive()) {\n\t\t\treturn false;\n\t\t}\n\t\tfinal Mob mob = entity.asMob();\n\t\t// Preserve the mod's original 3.5-block melee trigger, but do not treat mere\n\t\t// proximity as a successful melee opportunity. Minecraft's own melee reach\n\t\t// accounts for the entities' physical geometry; LOS rejects blocked targets.\n\t\t// This makes flying/elevated/unreachable close targets fall back to ranged\n\t\t// on the very next AI tick instead of waiting or staring.\n\t\treturn isInRangeToAttack(entity, target)\n\t\t\t\t&& mob.isWithinMeleeAttackRange(target)\n\t\t\t\t&& mob.getSensing().hasLineOfSight(target);\n\t}\n\n'''
if anchor not in text:
    raise SystemExit('Could not locate preferred-range helper anchor')
text = text.replace(anchor, helper + anchor, 1)

# While a valid projectile is loaded, the custom priority-0 ranged goal should own
# MOVE/LOOK unless the target is both inside the original close radius and genuinely
# melee-connectable. In that one case it yields immediately to normal Iron Golem melee.
old_can_use = '''\t\t@Override\n\t\tpublic boolean canUse() {\n\t\t\tthis.target = this.mob.getTarget();\n\t\t\treturn this.target != null && this.target.isAlive() && hasCompartmentContents(this.extraGolem);\n\t\t}\n\n\t\t@Override\n\t\tpublic boolean canContinueToUse() {\n\t\t\tthis.target = this.mob.getTarget();\n\t\t\treturn this.target != null && this.target.isAlive() && hasCompartmentContents(this.extraGolem);\n\t\t}\n'''
new_can_use = '''\t\t@Override\n\t\tpublic boolean canUse() {\n\t\t\tthis.target = this.mob.getTarget();\n\t\t\treturn this.target != null\n\t\t\t\t\t&& this.target.isAlive()\n\t\t\t\t\t&& hasAmmo(this.extraGolem)\n\t\t\t\t\t&& !shouldUseMeleeNow(this.extraGolem, this.target);\n\t\t}\n\n\t\t@Override\n\t\tpublic boolean canContinueToUse() {\n\t\t\tthis.target = this.mob.getTarget();\n\t\t\treturn this.target != null\n\t\t\t\t\t&& this.target.isAlive()\n\t\t\t\t\t&& hasAmmo(this.extraGolem)\n\t\t\t\t\t&& !shouldUseMeleeNow(this.extraGolem, this.target);\n\t\t}\n'''
if old_can_use not in text:
    raise SystemExit('Could not locate pass15 ranged goal canUse/canContinue block')
text = text.replace(old_can_use, new_can_use, 1)

# The independent firing loop must obey the exact same mode decision. Otherwise it
# could still launch projectiles while vanilla melee is active. Once melee ceases to
# be physically possible, this gate disappears immediately; there is no fallback timer.
tick_anchor = '''\t\t\tif (target == null || !target.isAlive() || !hasAmmo(entity)) {\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\t// No warmup and no maximum firing-distance gate.'''
tick_replacement = '''\t\t\tif (target == null || !target.isAlive() || !hasAmmo(entity)) {\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\t// Close + genuinely melee-connectable = pure melee for this tick. If the\n\t\t\t// target becomes unreachable (flying/elevated/blocked), this becomes false\n\t\t\t// on the next AI tick and ranged fire resumes with no additional delay.\n\t\t\tif (shouldUseMeleeNow(entity, target)) {\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\t// No warmup and no maximum firing-distance gate.'''
if tick_anchor not in text:
    raise SystemExit('Could not locate pass15 ranged tick gate anchor')
text = text.replace(tick_anchor, tick_replacement, 1)

# Update comments that still describe the pass15 "anything loaded = ranged only" rule.
text = text.replace(
    '''\t\t// Priority 0 and MOVE/LOOK flags suppress vanilla Iron Golem melee movement\n\t\t// whenever ANY item occupies the compartment. Empty compartment = normal melee.\n''',
    '''\t\t// Priority 0 and MOVE/LOOK flags own combat movement while usable projectile\n\t\t// ammo exists, except when a close target is genuinely melee-connectable.\n''',
    1
)
text = text.replace(
    '''\t\t// Never install the legacy ranged/melee goals here. The priority-0 ranged\n\t\t// position goal blocks normal melee whenever the compartment is non-empty;\n\t\t// when the compartment is empty it stops, exposing normal Iron Golem melee AI.\n''',
    '''\t\t// Never install the legacy ranged/melee goals here. The priority-0 ranged\n\t\t// position goal yields dynamically to normal Iron Golem melee when a close\n\t\t// target is physically strikeable, and immediately takes control back when it is not.\n''',
    1
)

shoot_path.write_text(text)

final = shoot_path.read_text()
for required in (
    'shouldUseMeleeNow(final IExtraGolem entity, final LivingEntity target)',
    'isInRangeToAttack(entity, target)',
    'mob.isWithinMeleeAttackRange(target)',
    'mob.getSensing().hasLineOfSight(target)',
    '&& hasAmmo(this.extraGolem)',
    '&& !shouldUseMeleeNow(this.extraGolem, this.target)',
    'if (shouldUseMeleeNow(entity, target))',
    'data.hasRangedShotCooldownElapsed(gameTime, getAttackInterval())',
    'DEFAULT_PREFERRED_MAX_RANGE = 15.0D',
    'POTION_PREFERRED_MAX_RANGE = 10.0D',
):
    if required not in final:
        raise SystemExit(f'Missing instant melee/ranged switch invariant: {required}')

# Guard against regressions to the discarded timer/strafe/retreat behavior.
for forbidden in (
    'RANGED_WARMUP_TICKS',
    'MELEE_FAILURE_FALLBACK_TICKS',
    'COMBAT_STRAFE_SPEED',
    'PREFERRED_MIN_RANGE',
):
    if forbidden in final:
        raise SystemExit(f'Forbidden old combat behavior survived pass16: {forbidden}')

print('Applied pass 16: instantaneous close-melee vs unreachable-ranged switching for Dispenser Golem.')
