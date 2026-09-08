from pathlib import Path
import re

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


old = '''\t\tmaintainConstructedNeutralRetaliation();\n\t\trecoverInterruptedDirectPlayerProvocation();\n'''
new = '''\t\tmaintainConstructedNeutralRetaliation();\n\t\trecoverInterruptedDirectPlayerProvocation();\n\t\tsanitizeSilentAggravationState();\n'''
replace_once(old, new, 'customServerAiStep silent-aggravation invariant call')

# Capture direct player provenance at the actual DamageSource hurt event. Derive the
# parameter name from the declaration so this survives Mojang/Yarn naming differences.
hurt_frag = ' boolean hurt('
pos = 0
method_start = method_brace = None
source_name = None
while True:
    i = s.find(hurt_frag, pos)
    if i < 0:
        break
    b = s.find('{', i)
    if b < 0:
        break
    decl = s[i:b]
    m = re.search(r'DamageSource\s+(\w+)', decl)
    if m:
        method_start, method_brace, source_name = i, b, m.group(1)
        break
    pos = i + len(hurt_frag)
if source_name is None:
    raise SystemExit('DamageSource hurt method/parameter missing')
insert_at = method_brace + 1
capture = f'''\n\t\tfinal Entity directProvocationSource = {source_name}.getEntity();\n\t\tif (directProvocationSource instanceof Player player\n\t\t\t\t&& !player.isCreative() && !player.isSpectator()) {{\n\t\t\tthis.interruptedDirectPlayerProvoker = player;\n\t\t}}\n'''
if 'final Entity directProvocationSource =' not in s:
    s = s[:insert_at] + capture + s[insert_at:]

replace_method('\tprivate void recoverInterruptedDirectPlayerProvocation()', r'''\tprivate void recoverInterruptedDirectPlayerProvocation() {
\t\tif (this.interruptedDirectPlayerProvoker == null || this.level().isClientSide()) {
\t\t\treturn;
\t\t}

\t\tfinal LivingEntity current = this.getTarget();
\t\tif (current != null && current.isAlive() && !(current instanceof Player)) {
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
\t\t\tconfigureBedrockNaturalIronGolemTargeting();
\t\t\treturn;
\t\t}

\t\tif (current == player) {
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
\t * Server-side aggression liveness invariant: no hidden provocation may survive without
\t * an actionable visible target. Legitimate state is promoted back into getTarget();
\t * stale state is destroyed so ordinary Iron-Golem hostile acquisition remains free.
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
\t\t\t\t\treturn;
\t\t\t\t}
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

\t\tthis.stopBeingAngry();
\t}
'''.replace('\\t', '\t'))

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
if 'final Entity directProvocationSource =' not in s:
    raise SystemExit('direct damage provenance capture missing')

p.write_text(s)
print(f'Applied no-silent-aggravation invariant using DamageSource parameter {source_name}.')