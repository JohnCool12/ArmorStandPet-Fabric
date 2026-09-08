from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s = p.read_text()


def replace_once(old, new, label):
    global s
    n=s.count(old)
    if n != 1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    s=s.replace(old,new,1)


def replace_method(signature, replacement):
    global s
    i=s.find(signature)
    if i < 0:
        raise SystemExit(f'method not found: {signature}')
    b=s.find('{',i)
    if b < 0:
        raise SystemExit(f'opening brace not found: {signature}')
    depth=0
    end=None
    for j in range(b,len(s)):
        if s[j]=='{': depth+=1
        elif s[j]=='}':
            depth-=1
            if depth==0:
                end=j+1
                break
    if end is None:
        raise SystemExit(f'closing brace not found: {signature}')
    s=s[:i]+replacement+s[end:]

# This transient remembers ONLY a player who directly provoked this exact golem and was
# temporarily displaced as the current target by a non-player. It is intentionally not
# persisted: normal vanilla anger/NBT remains authoritative across world reloads.
field_anchor='\tprivate boolean assigningVillageDefensePlayerTarget;\n'
if field_anchor not in s:
    raise SystemExit('assigningVillageDefensePlayerTarget field anchor missing')
replace_once(field_anchor,
    field_anchor +
    '\t@Nullable\n'
    '\tprivate UUID interruptedDirectPlayerProvoker;\n',
    'interrupted provoker field')

# Run recovery after vanilla has updated target/anger state and after one-time legacy
# migrations have repaired old entities, but before material behaviors tick.
old='''\t\tsuper.customServerAiStep();\n\t\tmigrateBedrockNaturalHostilityState();\n\t\tmigrateLegacyPlayerCreatedConstructedGolem();\n\t\tmaintainConstructedNeutralRetaliation();\n'''
new='''\t\tsuper.customServerAiStep();\n\t\tmigrateBedrockNaturalHostilityState();\n\t\tmigrateLegacyPlayerCreatedConstructedGolem();\n\t\tmaintainConstructedNeutralRetaliation();\n\t\trecoverInterruptedDirectPlayerProvocation();\n'''
replace_once(old,new,'customServerAiStep recovery call')

# The old strict-neutral runtime was superseded by natural-Iron-Golem behavior. Any old
# scoreboard-tagged entity that survives from those builds is upgraded immediately and
# NEVER strips persistent anger / lastHurt state every tick anymore.
replace_method('\tprivate void maintainConstructedNeutralRetaliation()', r'''\tprivate void maintainConstructedNeutralRetaliation() {
\t\tif (!isConstructedNeutral()) {
\t\t\treturn;
\t\t}

\t\t// Legacy strict-neutral tags are compatibility data only now. Convert them to
\t\t// the current natural-Iron-Golem target stack without erasing a legitimate
\t\t// current attacker/target/anger episode.
\t\tthis.removeTag(NEUTRAL_CONSTRUCTED_TAG);
\t\tthis.addTag(CONSTRUCTED_NATURAL_AI_TAG);
\t\tthis.constructedVillageTargetingActive = false;
\t\tthis.setPlayerCreated(false);
\t\tconfigureBedrockNaturalIronGolemTargeting();
\t}

\t/**
\t * Repairs the one target transition where Extra Golems could become combat-deadlocked:
\t * a directly provoking player is temporarily displaced by a hostile mob, then that mob
\t * dies. Vanilla 1.21.1 can rewrite NeutralMob persistent anger to the temporary mob, so
\t * we retain the LOCAL direct-player provenance separately. If that player is still a
\t * valid nearby survival target, resume the interrupted retaliation. Otherwise abandon
\t * the interruption cleanly so normal hostile-mob targeting can continue.
\t */
\tprivate void recoverInterruptedDirectPlayerProvocation() {
\t\tif (this.interruptedDirectPlayerProvoker == null || this.level().isClientSide()) {
\t\t\treturn;
\t\t}

\t\tfinal LivingEntity current = this.getTarget();
\t\tif (current != null && current.isAlive() && !(current instanceof Player)) {
\t\t\t// The temporary hostile target is still active; do not interfere.
\t\t\treturn;
\t\t}

\t\tfinal Player player = this.level().getServer() == null
\t\t\t\t? null
\t\t\t\t: this.level().getServer().getPlayerList().getPlayer(this.interruptedDirectPlayerProvoker);
\t\tfinal double follow = this.getAttributeValue(Attributes.FOLLOW_RANGE);
\t\tfinal boolean valid = player != null
\t\t\t\t&& player.isAlive()
\t\t\t\t&& !player.isCreative()
\t\t\t\t&& !player.isSpectator()
\t\t\t\t&& this.distanceToSqr(player) <= follow * follow;

\t\tif (!valid) {
\t\t\t// Creative/spectator/dead/out-of-range ends the remembered direct provocation.
\t\t\tif (this.getLastHurtByMob() != null
\t\t\t\t\t&& this.getLastHurtByMob().getUUID().equals(this.interruptedDirectPlayerProvoker)) {
\t\t\t\tthis.setLastHurtByMob(null);
\t\t\t}
\t\t\tif (current instanceof Player) {
\t\t\t\tthis.setTarget(null);
\t\t\t}
\t\t\tthis.interruptedDirectPlayerProvoker = null;
\t\t\t// Drop stale anger left on a dead temporary mob. This is the state that could
\t\t\t// otherwise keep the selector suspended until some unrelated player-state change.
\t\t\tif (this.getTarget() == null) {
\t\t\t\tthis.stopBeingAngry();
\t\t\t}
\t\t\treturn;
\t\t}

\t\t// Re-establish the same golem-local direct provocation. setLastHurtByMob is what
\t\t// HurtByTargetGoal normally consumes; the anger UUID also lets the vanilla angry-
\t\t// player goal reacquire naturally on subsequent ticks.
\t\tthis.setLastHurtByMob(player);
\t\tthis.setPersistentAngerTarget(player.getUUID());
\t\tif (this.getRemainingPersistentAngerTime() <= 0) {
\t\t\tthis.startPersistentAngerTimer();
\t\t}
\t\tthis.setTarget(player);
\t\tif (this.getTarget() == player) {
\t\t\tthis.interruptedDirectPlayerProvoker = null;
\t\t}
\t}
'''.replace('\\t','\t'))

# Remove the obsolete strict-neutral special case in hurt(). Natural GolemBase damage
# handling plus HurtByTargetGoal must own ordinary player provocation now. Bedrock's
# explicit damage-immune bookkeeping remains below this block and is untouched.
old='''\n\t\t\t// Strict individual neutrality for T-built Extra Golems. Only this golem\n\t\t\t// records the player who actually hit it; nearby golems receive no state.\n\t\t\tif (isConstructedNeutral() && !isConstructedNeutralInVillage()\n\t\t\t\t\t&& !isBedrockGolem()\n\t\t\t\t\t&& sourceEntity instanceof Player player\n\t\t\t\t\t&& !player.isCreative() && !player.isSpectator()) {\n\t\t\t\tthis.setPersistentAngerTarget(null);\n\t\t\t\tthis.setRemainingPersistentAngerTime(0);\n\t\t\t\tthis.setLastHurtByMob(player);\n\t\t\t\tthis.setTarget(player);\n\t\t\t}\n'''
if old in s:
    s=s.replace(old,'\n',1)
else:
    # Some cumulative reconstructions have the same block without the village predicate.
    old2='''\n\t\t\t// Strict individual neutrality for T-built Extra Golems. Only this golem\n\t\t\t// records the player who actually hit it; nearby golems receive no state.\n\t\t\tif (isConstructedNeutral() && sourceEntity instanceof Player player\n\t\t\t\t\t&& !player.isCreative() && !player.isSpectator()) {\n\t\t\t\tthis.setPersistentAngerTarget(null);\n\t\t\t\tthis.setRemainingPersistentAngerTime(0);\n\t\t\t\tthis.setLastHurtByMob(player);\n\t\t\t\tthis.setTarget(player);\n\t\t\t}\n'''
    if old2 not in s:
        raise SystemExit('obsolete strict hurt block not found')
    s=s.replace(old2,'\n',1)

# Remember a direct local player provoker when a non-player takes over the target. This
# sits immediately before super.setTarget(), so it sees the real old/new target pair.
old='''\t\tfinal LivingEntity oldTarget = this.getTarget();\n\t\tsuper.setTarget(pTarget);\n'''
new='''\t\tfinal LivingEntity oldTarget = this.getTarget();\n\t\tif (oldTarget instanceof Player player\n\t\t\t\t&& pTarget != null && !(pTarget instanceof Player)\n\t\t\t\t&& this.getLastHurtByMob() == player\n\t\t\t\t&& player.isAlive() && !player.isCreative() && !player.isSpectator()) {\n\t\t\tthis.interruptedDirectPlayerProvoker = player.getUUID();\n\t\t}\n\t\tsuper.setTarget(pTarget);\n\t\tif (pTarget instanceof Player player\n\t\t\t\t&& this.interruptedDirectPlayerProvoker != null\n\t\t\t\t&& this.interruptedDirectPlayerProvoker.equals(player.getUUID())\n\t\t\t\t&& this.getTarget() == player) {\n\t\t\tthis.interruptedDirectPlayerProvoker = null;\n\t\t}\n'''
replace_once(old,new,'setTarget interruption capture')

# Delete the old NBT downgrade that converted a perfectly natural PlayerCreated=false
# golem with persistent anger BACK into the obsolete strict-neutral PlayerCreated=true
# state. Old strict-tagged saves instead migrate forward to the current natural marker.
old='''\t\t} else {\n\t\t\tif (!isConstructedNeutral() && !this.isPlayerCreated() && this.getPersistentAngerTarget() != null) {\n\t\t\t\tthis.addTag(NEUTRAL_CONSTRUCTED_TAG);\n\t\t\t\tthis.setPlayerCreated(true);\n\t\t\t\tthis.setPersistentAngerTarget(null);\n\t\t\t\tthis.setRemainingPersistentAngerTime(0);\n\t\t\t\tthis.setLastHurtByMob(null);\n\t\t\t\tif (this.getTarget() instanceof Player) this.setTarget(null);\n\t\t\t}\n\t\t\tif (isConstructedNeutral()) {\n\t\t\t\tconfigureConstructedNeutralTargeting();\n\t\t\t}\n\t\t}\n'''
new='''\t\t} else {\n\t\t\tif (isConstructedNeutral()) {\n\t\t\t\tthis.removeTag(NEUTRAL_CONSTRUCTED_TAG);\n\t\t\t\tthis.addTag(CONSTRUCTED_NATURAL_AI_TAG);\n\t\t\t\tthis.setPlayerCreated(false);\n\t\t\t\tthis.constructedVillageTargetingActive = false;\n\t\t\t\tconfigureBedrockNaturalIronGolemTargeting();\n\t\t\t}\n\t\t}\n'''
replace_once(old,new,'remove NBT strict downgrade')

p.write_text(s)
print('Applied provoked-target interruption recovery and removed obsolete strict-neutral downgrade paths.')
