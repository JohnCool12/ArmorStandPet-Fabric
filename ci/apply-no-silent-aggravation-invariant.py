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

# Record direct player provenance at the actual damage event. The cumulative build stores
# this as a transient Player reference (not UUID), local to this exact golem. Insert at the
# beginning of hurt() so a competing hostile cannot overwrite lastHurtByMob first.
hurt_frag = ' boolean hurt('
i = s.find(hurt_frag)
if i < 0:
    raise SystemExit('hurt method fragment missing')
# Ensure this is the DamageSource overload rather than another boolean helper.
line_end = s.find('{', i)
if line_end < 0 or 'DamageSource' not in s[i:line_end]:
    # search forward for another hurt declaration containing DamageSource
    pos = i + len(hurt_frag)
    found = None
    while True:
        j = s.find(hurt_frag, pos)
        if j < 0:
            break
        b = s.find('{', j)
        if b >= 0 and 'DamageSource' in s[j:b]:
            found = (j, b)
            break
        pos = j + len(hurt_frag)
    if found is None:
        raise SystemExit('DamageSource hurt method missing')
    i, line_end = found
insert_at = line_end + 1
capture = '''\n\t\tfinal Entity directProvocationSource = pSource.getEntity();\n\t\tif (directProvocationSource instanceof Player player\n\t\t\t\t&& !player.isCreative() && !player.isSpectator()) {\n\t\t\tthis.interruptedDirectPlayerProvoker = player;\n\t\t}\n'''
if 'final Entity directProvocationSource = pSource.getEntity();' not in s:
    s = s[:insert_at] + capture + s[insert_at:]

# Replace the earlier narrow recovery with durable local-player provenance. A live
# non-player interruption is allowed to finish. Once it is gone, the original player is
# either visibly reacquired or the episode is explicitly cancelled and stale anger reset.
replace_method('\tprivate void recoverInterruptedDirectPlayerProvocation()', r'''\tprivate void recoverInterruptedDirectPlayerProvocation() {
\t\tif (this.interruptedDirectPlayerProvoker == null || this.level().isClientSide()) {
\t\t\treturn;
\t\t}

\t\tfinal LivingEntity current = this.getTarget();
\t\tif (current != null && current.isAlive() && !(current instanceof Player)) {
\t\t\t// A temporary non-player fight is visibly active. Preserve local player
\t\t\t// provenance without interfering with that fight.
\t\t\treturn;
\t\t}

\t\tfinal LivingEntity activeInterrupter = this.getLastHurtByMob();
\t\tif (activeInterrupter != null && activeInterrupter.isAlive() && !(activeInterrupter instanceof Player)) {
\t\t\treturn;
\t\t}

\t\tfinal Player player = this.interruptedDirectPlayerProvoker;
\t\tfinal double follow = this.getAttributeValue(Attributes.FOLLOW_RANGE);
\t\tfinal boolean valid = player != null
\t\t\t\t&& !player.isRemoved()
\t\t\t\t&& player.level() == this.level()
\t\t\t\t&& player.isAlive()
\t\t\t\t&& !player.isCreative()
\t\t\t\t&& !player.isSpectator()
\t\t\t\t&& this.distanceToSqr(player) <= follow * follow;

\t\tif (!valid) {
\t\t\tfinal LivingEntity staleAttacker = this.getLastHurtByMob();
\t\t\tif (staleAttacker == player || (staleAttacker != null && !staleAttacker.isAlive())) {
\t\t\t\tthis.setLastHurtByMob(null);
\t\t\t}
\t\t\tif (current instanceof Player || (current != null && !current.isAlive())) {
\t\t\t\tthis.setTarget(null);
\t\t\t}
\t\t\tthis.interruptedDirectPlayerProvoker = null;
\t\t\tthis.stopBeingAngry();
\t\t\t// removeAllGoals() in this helper safely stops TARGET-flag owners before the
\t\t\t// natural Iron-Golem target stack is reinstalled.
\t\t\tconfigureBedrockNaturalIronGolemTargeting();
\t\t\treturn;
\t\t}

\t\tif (current == player) {
\t\t\t// Provocation is already visible/actionable. Keep provenance until the
\t\t\t// episode genuinely ends, so a later mob interruption cannot erase it.
\t\t\treturn;
\t\t}

\t\tthis.setLastHurtByMob(player);
\t\tthis.setPersistentAngerTarget(player.getUUID());
\t\tif (this.getRemainingPersistentAngerTime() <= 0) {
\t\t\tthis.startPersistentAngerTimer();
\t\t}
\t\tthis.setTarget(player);
\t}

\t/**
\t * Server-side aggression liveness invariant.
\t *
\t * There is no valid state in which this golem is silently aggravated while having no
\t * actionable target. Legitimate live retaliation/anger is converted back into a real
\t * target immediately. Dead, missing, invalid, out-of-range or unjustified bookkeeping
\t * is cleared immediately so the normal Iron-Golem hostile target goals are never
\t * suppressed by invisible historical state.
\t */
\tprivate void sanitizeSilentAggravationState() {
\t\tif (this.level().isClientSide()) {
\t\t\treturn;
\t\t}

\t\tLivingEntity current = this.getTarget();
\t\tif (current != null) {
\t\t\tif (current.isAlive()) {
\t\t\t\tif (!(current instanceof Player player)
\t\t\t\t\t\t|| (!player.isCreative() && !player.isSpectator() && player.level() == this.level())) {
\t\t\t\t\t// A live visible target means aggravation is not silent; let its owning
\t\t\t\t\t// vanilla goal decide normal continuation/range semantics.
\t\t\t\t\treturn;
\t\t\t\t}
\t\t\t}
\t\t\t// Dead targets and players who became Creative/spectator are never allowed
\t\t\t// to pin hidden retaliation state.
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
\t\t\t\t\t\t&& !player.isRemoved()
\t\t\t\t\t\t&& !player.isCreative()
\t\t\t\t\t\t&& !player.isSpectator();
\t\t\t}
\t\t\tif (actionable) {
\t\t\t\tthis.setTarget(last);
\t\t\t\tif (this.getTarget() == last) {
\t\t\t\t\treturn;
\t\t\t\t}
\t\t\t}
\t\t\t// If a last-attacker record cannot become an actual target, it is stale.
\t\t\tthis.setLastHurtByMob(null);
\t\t}

\t\tfinal var angerId = this.getPersistentAngerTarget();
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
\t\t\t// A player anger UUID is never self-justifying. Require this golem's own
\t\t\t// direct provenance or vanilla village-reputation justification, preserving
\t\t\t// the existing anti-group-aggression guarantee.
\t\t\tfinal boolean justified = this.getLastHurtByMob() == player
\t\t\t\t\t|| hasVanillaVillageReputationReason(player)
\t\t\t\t\t|| this.interruptedDirectPlayerProvoker == player;
\t\t\tactionable = actionable
\t\t\t\t\t&& justified
\t\t\t\t\t&& player.level() == this.level()
\t\t\t\t\t&& !player.isRemoved()
\t\t\t\t\t&& !player.isCreative()
\t\t\t\t\t&& !player.isSpectator();
\t\t} else if (angry != null) {
\t\t\t// Non-player anger is meaningful only for this golem's own attacker or a
\t\t\t// normal Iron-Golem hostile target; Creepers remain excluded.
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

\t\t// This is the forbidden state: anger exists, but there is no target it can
\t\t// legitimately produce. Destroy the stale anger token immediately.
\t\tthis.stopBeingAngry();
\t}
'''.replace('\\t', '\t'))

# The prior recovery build cleared provenance as soon as player reacquisition succeeded.
# Durable provenance must instead survive until the provocation actually ends.
for old in (
    '''\t\tif (pTarget instanceof Player player\n\t\t\t\t&& this.interruptedDirectPlayerProvoker == player\n\t\t\t\t&& this.getTarget() == player) {\n\t\t\tthis.interruptedDirectPlayerProvoker = null;\n\t\t}\n''',
    '''\t\tif (pTarget instanceof Player player\n\t\t\t\t&& this.interruptedDirectPlayerProvoker != null\n\t\t\t\t&& this.interruptedDirectPlayerProvoker.equals(player.getUUID())\n\t\t\t\t&& this.getTarget() == player) {\n\t\t\tthis.interruptedDirectPlayerProvoker = null;\n\t\t}\n''',
):
    if old in s:
        s = s.replace(old, '', 1)

if 'private Player interruptedDirectPlayerProvoker;' not in s:
    raise SystemExit('direct Player provenance field missing after cumulative compile fix')
if 'sanitizeSilentAggravationState();' not in s:
    raise SystemExit('silent-aggravation invariant call missing')
if 'final Entity directProvocationSource = pSource.getEntity();' not in s:
    raise SystemExit('direct damage provenance capture missing')

p.write_text(s)
print('Applied no-silent-aggravation invariant using direct Player provenance.')