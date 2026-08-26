from pathlib import Path
import re

p = Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s = p.read_text()


def replace_method(signature: str, replacement: str, required: bool = True) -> bool:
    global s
    start = s.find(signature)
    if start < 0:
        if required:
            raise SystemExit(f'method not found: {signature}')
        return False
    brace = s.find('{', start)
    if brace < 0:
        raise SystemExit(f'opening brace not found: {signature}')
    depth = 0
    end = None
    for i in range(brace, len(s)):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise SystemExit(f'closing brace not found: {signature}')
    s = s[:start] + replacement + s[end:]
    return True


# TARGET ACQUISITION PRINCIPLE:
# GolemBase extends vanilla IronGolem. For acquisition we therefore delegate to / copy
# ONLY vanilla IronGolem behavior and remove the accumulated custom recovery/provenance
# machinery. Material-specific attack execution and Behavior hooks remain untouched.

# 1) Vanilla IronGolem registerGoals() is the authoritative source for BOTH ordinary
#    goals and the exact targetSelector stack. Extra material behaviors may subsequently
#    add ordinary goals, but must not mutate targetSelector.
replace_method('\t@Override\n\tprotected void registerGoals() {', '''\t@Override
\tprotected void registerGoals() {
\t\tsuper.registerGoals();
\t}''')

# 2) Every time setGolemId reinitializes goals, clear BOTH selectors through GoalSelector's
#    API before calling vanilla registerGoals. The original mod only cleared goalSelector,
#    which could accumulate duplicate vanilla target goals across material reinitialization.
old = '''\t\t\t// remove and re-instantiate goals\n\t\t\tthis.goalSelector.getAvailableGoals().clear();\n\t\t\tthis.registerGoals();\n'''
new = '''\t\t\t// Rebuild from a clean state. removeAllGoals invokes stop() on active goals,\n\t\t\t// releasing TARGET controls instead of leaving stale WrappedGoal state.\n\t\t\tthis.goalSelector.removeAllGoals(goal -> true);\n\t\t\tthis.targetSelector.removeAllGoals(goal -> true);\n\t\t\tthis.registerGoals();\n'''
if old not in s:
    # Some cumulative builds already changed the goalSelector clear to removeAllGoals.
    old = '''\t\t\t// remove and re-instantiate goals\n\t\t\tthis.goalSelector.removeAllGoals(goal -> true);\n\t\t\tthis.registerGoals();\n'''
if old not in s:
    raise SystemExit('setGolemId goal rebuild block not found')
s = s.replace(old, new, 1)

# 3) No Extra-Golem-specific target admission policy. IronGolem.canAttackType() already
#    contains vanilla PlayerCreated and Creeper rules; delegate to it exactly.
replace_method('\t@Override\n\tpublic boolean canAttackType(final EntityType<?> type) {', '''\t@Override
\tpublic boolean canAttackType(final EntityType<?> type) {
\t\treturn super.canAttackType(type);
\t}''')

# 4) No custom player-target provenance, reputation authentication, Creative barriers,
#    or interrupted-provoker bookkeeping in setTarget. Vanilla target goals own it.
replace_method('\t@Override\n\tpublic void setTarget(@Nullable LivingEntity pTarget) {', '''\t@Override
\tpublic void setTarget(@Nullable LivingEntity pTarget) {
\t\tsuper.setTarget(pTarget);
\t}''')

# 5) Revert the pre-AI hard-reset hook. Creative/spectator/death/anger transitions must
#    pass through vanilla IronGolem/NeutralMob target-goal lifecycle instead.
pre_ai = '''\t@Override\n\tpublic void tick() {\n\t\tif (!this.level().isClientSide()) {\n\t\t\thardResetInvalidPlayerProvocationBeforeAiTick();\n\t\t}\n\t\tsuper.tick();\n'''
if pre_ai in s:
    s = s.replace(pre_ai, '''\t@Override\n\tpublic void tick() {\n\t\tsuper.tick();\n''', 1)
else:
    raise SystemExit('creative hard-reset tick preamble not found')

# 6) Remove every custom target-recovery/migration call from the live server AI tick.
#    The methods may remain as dead compatibility code, but cannot participate in runtime
#    target acquisition. Vanilla IronGolem.aiStep/updatePersistentAnger remains inherited.
for call in (
    '\t\tmigrateBedrockNaturalHostilityState();\n',
    '\t\tmigrateLegacyPlayerCreatedConstructedGolem();\n',
    '\t\tmaintainConstructedNeutralRetaliation();\n',
    '\t\trecoverInterruptedDirectPlayerProvocation();\n',
    '\t\tsanitizeSilentAggravationState();\n',
):
    s = s.replace(call, '')

# 7) The old helper had accumulated wrappers/guards. If any compatibility/load path calls
#    it, its result must still be the EXACT targetSelector portion of vanilla 1.21.1
#    IronGolem.registerGoals().
replace_method('\tprivate void configureBedrockNaturalIronGolemTargeting() {', '''\tprivate void configureBedrockNaturalIronGolemTargeting() {
\t\tthis.targetSelector.removeAllGoals(goal -> true);
\t\tthis.targetSelector.addGoal(1, new DefendVillageTargetGoal(this));
\t\tthis.targetSelector.addGoal(2, new HurtByTargetGoal(this));
\t\tthis.targetSelector.addGoal(3, new NearestAttackableTargetGoal<>(this, Player.class, 10, true, false, this::isAngryAt));
\t\tthis.targetSelector.addGoal(3, new NearestAttackableTargetGoal<>(this, Mob.class, 5, false, false,
\t\t\t\tentity -> entity instanceof Enemy && !(entity instanceof Creeper)));
\t\tthis.targetSelector.addGoal(4, new ResetUniversalAngerTargetGoal<>(this, false));
\t}''')

# Any obsolete strict/hybrid selector helper that somehow gets called must resolve to the
# vanilla target stack rather than creating a second target model.
replace_method('\tprivate void configureConstructedNeutralTargeting() {', '''\tprivate void configureConstructedNeutralTargeting() {
\t\tconfigureBedrockNaturalIronGolemTargeting();
\t}''', required=False)

# 8) Constructed Extra Golems intentionally retain the project's established NATURAL
#    Iron-Golem semantics (PlayerCreated=false), but construction itself must not clear,
#    synthesize, or force target/anger state. This is the only semantic choice outside
#    vanilla acquisition: it selects the natural-village IronGolem branch rather than the
#    player-created branch, matching the behavior requested throughout this project.
replace_method('\tpublic void markConstructedNeutral() {', '''\tpublic void markConstructedNeutral() {
\t\tthis.removeTag(NEUTRAL_CONSTRUCTED_TAG);
\t\tthis.addTag(CONSTRUCTED_NATURAL_AI_TAG);
\t\tthis.constructedVillageTargetingActive = false;
\t\tthis.setPlayerCreated(false);
\t\tif (isBedrockGolem()) {
\t\t\tthis.addTag(BEDROCK_NATURAL_HOSTILITY_TAG);
\t\t}
\t}''')

# Village-summoned Extra Golems are likewise natural golems. Do not touch active targeting
# state here; merely establish PlayerCreated=false if this helper exists.
replace_method('\tpublic void markVillageSummonedNatural() {', '''\tpublic void markVillageSummonedNatural() {
\t\tthis.setPlayerCreated(false);
\t}''', required=False)

# 9) Preserve vanilla NeutralMob anger loaded by IronGolem.readAdditionalSaveData. Remove
#    all old target-state migration/cleanup inserted between Extra-Golem container and
#    variant reads; only normalize the desired natural PlayerCreated semantic.
read_sig = '\t@Override\n\tpublic void readAdditionalSaveData(CompoundTag tag) {'
rstart = s.find(read_sig)
if rstart < 0:
    # tolerate final parameter spelling
    m = re.search(r'\t@Override\n\tpublic void readAdditionalSaveData\([^\n]+\) \{', s)
    if not m:
        raise SystemExit('readAdditionalSaveData method missing')
    rstart = m.start()
rbrace = s.find('{', rstart)
depth = 0
rend = None
for i in range(rbrace, len(s)):
    if s[i] == '{': depth += 1
    elif s[i] == '}':
        depth -= 1
        if depth == 0:
            rend = i + 1
            break
if rend is None:
    raise SystemExit('unclosed readAdditionalSaveData')
rbody = s[rstart:rend]
container_i = rbody.find('\t\treadContainer(tag);')
variant_i = rbody.find('\t\treadVariant(tag);')
if container_i >= 0 and variant_i > container_i:
    after_container = container_i + len('\t\treadContainer(tag);')
    rbody = (rbody[:after_container]
             + '\n\t\t// Preserve vanilla loaded anger/target history; only select natural-golem semantics.\n'
             + '\t\tthis.removeTag(NEUTRAL_CONSTRUCTED_TAG);\n'
             + '\t\tthis.addTag(CONSTRUCTED_NATURAL_AI_TAG);\n'
             + '\t\tthis.setPlayerCreated(false);\n'
             + '\t\tif (isBedrockGolem()) this.addTag(BEDROCK_NATURAL_HOSTILITY_TAG);\n'
             + rbody[variant_i:])
    s = s[:rstart] + rbody + s[rend:]
else:
    raise SystemExit('readAdditionalSaveData container/variant boundaries missing')

# 10) Remove direct-player provenance capture from hurt(). It was part of the custom
#     recovery system. Bedrock's separate minimal setLastHurtByMob bridge remains because
#     its deliberate damage immunity would otherwise prevent a vanilla retaliation
#     stimulus from ever reaching HurtByTargetGoal.
s = re.sub(
    r'\n\t\tfinal Entity directProvocationSource = [^;]+;\n'
    r'\t\tif \(directProvocationSource instanceof Player player\n'
    r'\t\t\t\t&& !player\.isCreative\(\) && !player\.isSpectator\(\)\) \{\n'
    r'\t\t\tthis\.interruptedDirectPlayerProvoker = player;\n'
    r'\t\t\}\n',
    '\n', s, count=1)

# 11) No Extra-Golem behavior implementation is allowed to add targetSelector goals.
#     (The build workflow also scans this after reconstruction.)

# Static invariants for this patch.
for forbidden_live in (
    '\t\thardResetInvalidPlayerProvocationBeforeAiTick();',
    '\t\trecoverInterruptedDirectPlayerProvocation();',
    '\t\tsanitizeSilentAggravationState();',
    '\t\tmaintainConstructedNeutralRetaliation();',
    '\t\tmigrateLegacyPlayerCreatedConstructedGolem();',
    '\t\tmigrateBedrockNaturalHostilityState();',
):
    if forbidden_live in s:
        raise SystemExit(f'custom target-acquisition call still live: {forbidden_live.strip()}')

if 'public void setTarget(@Nullable LivingEntity pTarget) {\n\t\tsuper.setTarget(pTarget);\n\t}' not in s:
    raise SystemExit('setTarget is not pure vanilla delegation')
if 'return super.canAttackType(type);' not in s:
    raise SystemExit('canAttackType is not vanilla delegation')
if 'this.targetSelector.removeAllGoals(goal -> true);\n\t\t\tthis.registerGoals();' not in s:
    raise SystemExit('setGolemId does not cleanly rebuild vanilla target selector')

p.write_text(s)
print('Applied strict vanilla 1.21.1 Iron Golem target-acquisition parity to Extra Golems.')
