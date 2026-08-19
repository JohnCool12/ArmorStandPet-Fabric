from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s = p.read_text()


def replace_once(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    s = s.replace(old, new, 1)


def replace_method(signature, replacement):
    global s
    i = s.find(signature)
    if i < 0:
        raise SystemExit(f'method not found: {signature}')
    b = s.find('{', i)
    if b < 0:
        raise SystemExit(f'opening brace not found: {signature}')
    depth = 0
    end = None
    for j in range(b, len(s)):
        if s[j] == '{':
            depth += 1
        elif s[j] == '}':
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    if end is None:
        raise SystemExit(f'closing brace not found: {signature}')
    s = s[:i] + replacement + s[end:]

# Run the liveness/sanitation invariant immediately after direct-provoker recovery.
old = '''\t\tmaintainConstructedNeutralRetaliation();\n\t\trecoverInterruptedDirectPlayerProvocation();\n'''
new = '''\t\tmaintainConstructedNeutralRetaliation();\n\t\trecoverInterruptedDirectPlayerProvocation();\n\t\tsanitizeSilentAggravationState();\n'''
replace_once(old, new, 'customServerAiStep silent-aggravation invariant call')

# Record a direct player provoker at the damage event itself. This is deliberately local
# to this exact golem and does not use alertOthers/group propagation. Recording here
# closes the race where another mob can overwrite lastHurtByMob before setTarget switches.
anchor = '\t\tfinal Entity sourceEntity = pSource.getEntity();\n'
if anchor not in s:
    raise SystemExit('hurt sourceEntity anchor missing')
replace_once(anchor, anchor + '''\t\tif (sourceEntity instanceof Player player\n\t\t\t\t&& !player.isCreative() && !player.isSpectator()) {\n\t\t\tthis.interruptedDirectPlayerProvoker = player.getUUID();\n\t\t}\n''', 'direct provoker damage capture')

# Replace the previous narrow recovery with a durable local-provoker recovery. The UUID
# remains remembered while the provoking player is actively being fought or while a live
# non-player temporarily owns the target. It is discarded as soon as the player ceases to
# be a valid actionable target.
replace_method('\tprivate void recoverInterruptedDirectPlayerProvocation()', r'''\tprivate void recoverInterruptedDirectPlayerProvocation() {
\t\tif (this.interruptedDirectPlayerProvoker == null || this.level().isClientSide()) {
\t\t\treturn;
\t\t}

\t\tfinal LivingEntity current = this.getTarget();
\t\tif (current != null && current.isAlive() && !(current instanceof Player)) {
\t\t\t// A temporary non-player fight is visibly active; preserve the direct-player
\t\t\t// provenance but do not interfere until that target is gone.
\t\t\treturn;
\t\t}

\t\tfinal Player player = this.level().getServer() == null
\t\t\t\t? null
\t\t\t\t: this.level().getServer().getPlayerList().getPlayer(this.interruptedDirectPlayerProvoker);
\t\tfinal double follow = this.getAttributeValue(Attributes.FOLLOW_RANGE);
\t\tfinal boolean valid = player != null
\t\t\t\t&& player.level() == this.level()
\t\t\t\t&& player.isAlive()
\t\t\t\t&& !player.isCreative()
\t\t\t\t&& !player.isSpectator()
\t\t\t\t&& this.distanceToSqr(player) <= follow * follow;

\t\tif (!valid) {
\t\t\tif (this.getLastHurtByMob() != null
\t\t\t\t\t&& this.getLastHurtByMob().getUUID().equals(this.interruptedDirectPlayerProvoker)) {
\t\t\t\tthis.setLastHurtByMob(null);
\t\t\t}
\t\t\tif (current instanceof Player) {
\t\t\t\tthis.setTarget(null);
\t\t\t}
\t\t\tthis.interruptedDirectPlayerProvoker = null;
\t\t\t// If there is no visible target, never leave a hidden anger token behind.
\t\t\tif (this.getTarget() == null) {
\t\t\t\tthis.stopBeingAngry();
\t\t\t}
\t\t\treturn;
\t\t}

\t\tif (current == player) {
\t\t\t// The provocation is already visible and actionable. Keep the provenance so a
\t\t\t// later non-player interruption cannot erase it before we see the transition.
\t\t\treturn;
\t\t}

\t\t// No live temporary target remains. Re-establish the golem-local direct
\t\t// provocation immediately rather than leaving silent anger/last-hurt state.
\t\tthis.setLastHurtByMob(player);
\t\tthis.setPersistentAngerTarget(player.getUUID());
\t\tif (this.getRemainingPersistentAngerTime() <= 0) {
\t\t\tthis.startPersistentAngerTimer();
\t\t}
\t\tthis.setTarget(player);
\t}

\t/**
\t * Server-side liveness invariant for all aggression bookkeeping.
\t *
\t * Extra Golems are not allowed to remain in a hidden aggravated state with no
\t * actionable target. A valid direct attacker / legitimate village-reputation target /
\t * live hostile anger target is made visible by immediately restoring getTarget(). Any
\t * dead, missing, creative, spectator, out-of-range, unjustified, or otherwise stale
\t * retaliation/anger record is cleared so the normal Iron-Golem hostile target goals
\t * remain free to acquire mobs on the next selector tick.
\t */
\tprivate void sanitizeSilentAggravationState() {
\t\tif (this.level().isClientSide()) {
\t\t\treturn;
\t\t}

\t\tLivingEntity current = this.getTarget();
\t\tif (current != null) {
\t\t\tif (current.isAlive()) {
\t\t\t\t// An actual live target means there is no silent aggravation to repair.
\t\t\t\treturn;
\t\t\t}
\t\t\tthis.setTarget(null);
\t\t\tcurrent = null;
\t\t}

\t\tfinal double follow = this.getAttributeValue(Attributes.FOLLOW_RANGE);
\t\tLivingEntity last = this.getLastHurtByMob();
\t\tif (last != null && !last.isAlive()) {
\t\t\tthis.setLastHurtByMob(null);
\t\t\tlast = null;
\t\t}

\t\tif (last != null) {
\t\t\tboolean actionable = this.canAttack(last)
\t\t\t\t\t&& this.distanceToSqr(last) <= follow * follow;
\t\t\tif (last instanceof Player player) {
\t\t\t\tactionable = actionable
\t\t\t\t\t\t&& player.level() == this.level()
\t\t\t\t\t\t&& !player.isCreative()
\t\t\t\t\t\t&& !player.isSpectator();
\t\t\t}
\t\t\tif (actionable) {
\t\t\t\tthis.setTarget(last);
\t\t\t\tif (this.getTarget() == last) {
\t\t\t\t\treturn;
\t\t\t\t}
\t\t\t}
\t\t\t// A retaliation record that cannot become a real target is stale by
\t\t\t// definition and must not continue suppressing ordinary target acquisition.
\t\t\tthis.setLastHurtByMob(null);
\t\t}

\t\tfinal UUID angerId = this.getPersistentAngerTarget();
\t\tif (angerId == null) {
\t\t\treturn;
\t\t}

\t\tLivingEntity angry = null;
\t\tif (this.level() instanceof ServerLevel serverLevel) {
\t\t\tfinal Entity candidate = serverLevel.getEntity(angerId);
\t\t\tif (candidate instanceof LivingEntity living) {
\t\t\t\tangry = living;
\t\t\t}
\t\t}

\t\tboolean actionable = angry != null
\t\t\t\t&& angry.isAlive()
\t\t\t\t&& this.canAttack(angry)
\t\t\t\t&& this.distanceToSqr(angry) <= follow * follow;

\t\tif (angry instanceof Player player) {
\t\t\t// A player anger UUID is not, by itself, sufficient provenance. It must still
\t\t\t// correspond to this golem's own direct attacker or to vanilla village
\t\t\t// reputation. This preserves the anti-group-aggression guarantee.
\t\t\tfinal boolean justified = this.getLastHurtByMob() == player
\t\t\t\t\t|| hasVanillaVillageReputationReason(player)
\t\t\t\t\t|| (this.interruptedDirectPlayerProvoker != null
\t\t\t\t\t\t\t&& this.interruptedDirectPlayerProvoker.equals(player.getUUID()));
\t\t\tactionable = actionable
\t\t\t\t\t&& justified
\t\t\t\t\t&& player.level() == this.level()
\t\t\t\t\t&& !player.isCreative()
\t\t\t\t\t&& !player.isSpectator();
\t\t} else if (angry != null) {
\t\t\t// Non-player persistent anger is actionable only when it is a real direct
\t\t\t// attacker or a vanilla-style hostile mob (never a Creeper).
\t\t\tactionable = actionable && (this.getLastHurtByMob() == angry
\t\t\t\t\t|| (angry instanceof net.minecraft.world.entity.monster.Enemy
\t\t\t\t\t\t\t&& !(angry instanceof net.minecraft.world.entity.monster.Creeper)));
\t\t}

\t\tif (actionable) {
\t\t\tthis.setTarget(angry);
\t\t\tif (this.getTarget() == angry) {
\t\t\t\treturn;
\t\t\t}
\t\t}

\t\t// Missing/dead/unjustified/out-of-range anger is the exact silent state this
\t\t// invariant forbids. Clear it immediately; normal target goals remain installed.
\t\tthis.stopBeingAngry();
\t}
'''.replace('\\t', '\t'))

# The older recovery cleared provenance as soon as setTarget(player) succeeded. Remove that
# behavior if it remains after replacing the method/setTarget logic, because the durable
# provenance must survive until the provocation actually ends.
old = '''\t\tif (pTarget instanceof Player player\n\t\t\t\t&& this.interruptedDirectPlayerProvoker != null\n\t\t\t\t&& this.interruptedDirectPlayerProvoker.equals(player.getUUID())\n\t\t\t\t&& this.getTarget() == player) {\n\t\t\tthis.interruptedDirectPlayerProvoker = null;\n\t\t}\n'''
if old in s:
    s = s.replace(old, '', 1)

p.write_text(s)
print('Applied no-silent-aggravation invariant and durable direct-provoker provenance.')