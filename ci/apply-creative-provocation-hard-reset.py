from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s = p.read_text()


def replace_once(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    s = s.replace(old, new, 1)


# Run invalid-player cancellation BEFORE super.tick(), so stale player retaliation cannot
# participate in the next target-selector/navigation cycle at all.
tick_old = '''\t@Override\n\tpublic void tick() {\n\t\tsuper.tick();\n'''
tick_new = '''\t@Override\n\tpublic void tick() {\n\t\tif (!this.level().isClientSide()) {\n\t\t\thardResetInvalidPlayerProvocationBeforeAiTick();\n\t\t}\n\t\tsuper.tick();\n'''
replace_once(tick_old, tick_new, 'pre-AI hard reset insertion')

# Insert the hard reset helpers immediately before tick().
anchor = '''\t@Override\n\tpublic void tick() {\n\t\tif (!this.level().isClientSide()) {\n'''
helpers = r'''\tprivate boolean isInvalidPlayerCombatTarget(@Nullable final Player player) {
\t\treturn player == null
\t\t\t\t|| player.isRemoved()
\t\t\t\t|| player.level() != this.level()
\t\t\t\t|| !player.isAlive()
\t\t\t\t|| player.isCreative()
\t\t\t\t|| player.isSpectator();
\t}

\tprivate boolean isInvalidRememberedPlayerProvoker(@Nullable final Player player) {
\t\tif (isInvalidPlayerCombatTarget(player)) {
\t\t\treturn true;
\t\t}
\t\tfinal double follow = this.getAttributeValue(Attributes.FOLLOW_RANGE);
\t\treturn this.distanceToSqr(player) > follow * follow;
\t}

\t/**
\t * Pre-AI cancellation barrier for player provocation. Creative/spectator/dead/removed/
\t * wrong-dimension players must never survive in any of the independent retaliation
\t * bookkeeping fields long enough to reserve TARGET control or poison hostile reacquisition.
\t *
\t * Hidden direct-provoker state is cleared even while a legitimate hostile mob is the
\t * current target. If the invalid player WAS the current target (or the golem is idle),
\t * the target selector is safely restarted and a normal hostile target is seeded at once.
\t */
\tprivate void hardResetInvalidPlayerProvocationBeforeAiTick() {
\t\tif (this.level().isClientSide()) {
\t\t\treturn;
\t\t}

\t\tboolean clearedPlayerProvocation = false;
\t\tboolean clearedCurrentPlayerTarget = false;

\t\tfinal LivingEntity current = this.getTarget();
\t\tif (current instanceof Player player && isInvalidPlayerCombatTarget(player)) {
\t\t\tthis.setTarget(null);
\t\t\tclearedPlayerProvocation = true;
\t\t\tclearedCurrentPlayerTarget = true;
\t\t}

\t\tfinal LivingEntity last = this.getLastHurtByMob();
\t\tif (last instanceof Player player && isInvalidRememberedPlayerProvoker(player)) {
\t\t\tthis.setLastHurtByMob(null);
\t\t\tclearedPlayerProvocation = true;
\t\t}

\t\tif (this.interruptedDirectPlayerProvoker != null
\t\t\t\t&& isInvalidRememberedPlayerProvoker(this.interruptedDirectPlayerProvoker)) {
\t\t\tthis.interruptedDirectPlayerProvoker = null;
\t\t\tclearedPlayerProvocation = true;
\t\t}

\t\tfinal java.util.UUID angerId = this.getPersistentAngerTarget();
\t\tif (angerId != null && this.level() instanceof ServerLevel serverLevel) {
\t\t\tfinal Entity angryEntity = serverLevel.getEntity(angerId);
\t\t\tif (angryEntity instanceof Player player && isInvalidRememberedPlayerProvoker(player)) {
\t\t\t\tthis.stopBeingAngry();
\t\t\t\tclearedPlayerProvocation = true;
\t\t\t} else if (angryEntity == null && clearedPlayerProvocation && this.getTarget() == null) {
\t\t\t\t// A vanished player/dimension transition can leave an unresolvable anger UUID.
\t\t\t\tthis.stopBeingAngry();
\t\t\t}
\t\t}

\t\tif (!clearedPlayerProvocation) {
\t\t\treturn;
\t\t}

\t\t// Do not interrupt a real non-player fight just to clean hidden player bookkeeping.
\t\tfinal LivingEntity afterCleanup = this.getTarget();
\t\tif (afterCleanup != null && afterCleanup.isAlive() && !(afterCleanup instanceof Player)) {
\t\t\treturn;
\t\t}

\t\tif (clearedCurrentPlayerTarget || afterCleanup == null) {
\t\t\tthis.setTarget(null);
\t\t\tthis.getNavigation().stop();
\t\t\tthis.setAggressive(false);
\t\t\t// removeAllGoals() invokes WrappedGoal.stop(), releasing TARGET flags correctly.
\t\t\tconfigureBedrockNaturalIronGolemTargeting();
\t\t\tseedNearestNormalHostileTarget();
\t\t}
\t}

\t/** Immediately reseed the same hostile category used by the natural Iron-Golem target stack. */
\tprivate void seedNearestNormalHostileTarget() {
\t\tif (!(this.level() instanceof ServerLevel serverLevel) || this.getTarget() != null) {
\t\t\treturn;
\t\t}
\t\tfinal double follow = this.getAttributeValue(Attributes.FOLLOW_RANGE);
\t\tfinal net.minecraft.world.phys.AABB box = this.getBoundingBox().inflate(follow, follow, follow);
\t\tMob nearest = null;
\t\tdouble nearestDistance = follow * follow;
\t\tfor (Mob candidate : serverLevel.getEntitiesOfClass(Mob.class, box, candidate ->
\t\t\t\tcandidate != this
\t\t\t\t\t\t&& candidate.isAlive()
\t\t\t\t\t\t&& candidate instanceof Enemy
\t\t\t\t\t\t&& !(candidate instanceof Creeper)
\t\t\t\t\t\t&& this.canAttack(candidate))) {
\t\t\tfinal double distance = this.distanceToSqr(candidate);
\t\t\tif (distance <= nearestDistance) {
\t\t\t\tnearestDistance = distance;
\t\t\t\tnearest = candidate;
\t\t\t}
\t\t}
\t\tif (nearest != null) {
\t\t\tthis.setTarget(nearest);
\t\t}
\t}

'''.replace('\\t', '\t')
if anchor not in s:
    raise SystemExit('tick helper anchor missing')
s = s.replace(anchor, helpers + anchor, 1)

# Harden the target setter itself: no provenance/anger state is ever sufficient to make
# an invalid Creative/spectator/dead/removed player a target again after cleanup.
set_anchor = '''\t@Override\n\tpublic void setTarget(@Nullable LivingEntity pTarget) {\n\t\t// Direct retaliation must remain individual'''
set_repl = '''\t@Override\n\tpublic void setTarget(@Nullable LivingEntity pTarget) {\n\t\tif (pTarget instanceof Player player && isInvalidPlayerCombatTarget(player)) {\n\t\t\tif (this.getTarget() == player) {\n\t\t\t\tsuper.setTarget(null);\n\t\t\t}\n\t\t\treturn;\n\t\t}\n\n\t\t// Direct retaliation must remain individual'''
replace_once(set_anchor, set_repl, 'invalid-player setTarget barrier')

for token in (
    'hardResetInvalidPlayerProvocationBeforeAiTick();',
    'private void hardResetInvalidPlayerProvocationBeforeAiTick()',
    'private void seedNearestNormalHostileTarget()',
    'this.getNavigation().stop();',
    'this.setAggressive(false);',
    'configureBedrockNaturalIronGolemTargeting();',
    'candidate instanceof Enemy',
    'isInvalidPlayerCombatTarget(player)',
):
    if token not in s:
        raise SystemExit(f'missing creative-provocation reset token: {token}')

p.write_text(s)
print('Applied pre-AI Creative/spectator provocation hard reset and immediate hostile reacquisition.')
