from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
text = p.read_text()


def replace_method(signature: str, replacement: str) -> None:
    global text
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'Missing method signature: {signature}')
    if text.find(signature, start + 1) >= 0:
        raise SystemExit(f'Duplicate method signature: {signature}')
    brace = text.find('{', start)
    depth = 0
    end = None
    for i in range(brace, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise SystemExit(f'Unclosed method: {signature}')
    text = text[:start] + replacement + text[end:]


# All pumpkin/T-shape-built Extra Golems now use the same target semantics as a
# naturally spawned vanilla Iron Golem everywhere. There is intentionally NO
# ServerLevel.isVillage gate around DefendVillageTargetGoal: vanilla does not have one.
# DefendVillageTargetGoal itself searches nearby villagers and their gossip/reputation.
marker = '\tprivate static final String BEDROCK_NATURAL_HOSTILITY_TAG = "extra_golems_bedrock_true_vanilla_natural_ai_v4";\n'
if marker not in text:
    raise SystemExit('Missing Bedrock natural-AI marker')
text = text.replace(marker, marker + '\tprivate static final String CONSTRUCTED_NATURAL_AI_TAG = "extra_golems_constructed_true_natural_ai_v1";\n', 1)

# The existing Bedrock helper is already an exact copy of the vanilla natural Iron
# Golem target stack. Reuse it for every T-built Extra Golem.
replace_method(
    '\tpublic void markConstructedNeutral() {',
    '''\tpublic void markConstructedNeutral() {
\t\tthis.removeTag(NEUTRAL_CONSTRUCTED_TAG);
\t\tthis.addTag(CONSTRUCTED_NATURAL_AI_TAG);
\t\tthis.constructedVillageTargetingActive = false;
\t\tthis.setPlayerCreated(false);
\t\tthis.stopBeingAngry();
\t\tthis.setLastHurtByMob(null);
\t\tthis.setTarget(null);
\t\tconfigureBedrockNaturalIronGolemTargeting();
\t\tif (isBedrockGolem()) {
\t\t\tthis.addTag(BEDROCK_NATURAL_HOSTILITY_TAG);
\t\t}
\t}'''
)

# Vanilla DefendVillageTargetGoal finds nearby villagers with
# TargetingConditions.forCombat(). GolemBase historically rejected VILLAGER in
# canAttackType(), so those villagers were filtered out before reputation was ever
# evaluated. Natural Iron Golems do not have that extra Villager exclusion. Removing
# it does not add a villager attack goal; it only lets vanilla village-defense AI see
# villagers for reputation checks.
old_villager_guard = 'if (type == EntityType.VILLAGER || type == EGRegistry.EntityReg.GOLEM.get()'
new_villager_guard = 'if (type == EGRegistry.EntityReg.GOLEM.get()'
if text.count(old_villager_guard) != 1:
    raise SystemExit(f'Expected one Villager canAttackType exclusion, found {text.count(old_villager_guard)}')
text = text.replace(old_villager_guard, new_villager_guard, 1)

# Prevent the old strict-neutral compatibility heuristic from converting a naturalized
# constructed golem back to PlayerCreated=true after its first player fight.
old = '''\t\tif (!isBedrockGolem() && !isConstructedNeutral() && !this.isPlayerCreated()
\t\t\t\t&& (this.getLastHurtByMob() instanceof Player || this.getTarget() instanceof Player)) {'''
new = '''\t\tif (!this.getTags().contains(CONSTRUCTED_NATURAL_AI_TAG)
\t\t\t\t&& !isBedrockGolem() && !isConstructedNeutral() && !this.isPlayerCreated()
\t\t\t\t&& (this.getLastHurtByMob() instanceof Player || this.getTarget() instanceof Player)) {'''
if text.count(old) != 1:
    raise SystemExit(f'Expected one legacy migration condition, found {text.count(old)}')
text = text.replace(old, new, 1)

# Existing T-built golems from the older strict/hybrid versions carry the old neutral
# tag. Upgrade them on the first server tick. Once upgraded they no longer enter any of
# the custom strict/hybrid maintenance logic.
maint_sig = '\tprivate void maintainConstructedNeutralRetaliation() {'
start = text.find(maint_sig)
if start < 0:
    raise SystemExit('Missing strict-neutral maintenance method')
brace = text.find('{', start)
insert = '''
\t\tif (!isBedrockGolem() && isConstructedNeutral()) {
\t\t\tthis.removeTag(NEUTRAL_CONSTRUCTED_TAG);
\t\t\tthis.addTag(CONSTRUCTED_NATURAL_AI_TAG);
\t\t\tthis.constructedVillageTargetingActive = false;
\t\t\tthis.setPlayerCreated(false);
\t\t\tthis.stopBeingAngry();
\t\t\tthis.setLastHurtByMob(null);
\t\t\tthis.setTarget(null);
\t\t\tconfigureBedrockNaturalIronGolemTargeting();
\t\t\treturn;
\t\t}
'''
text = text[:brace + 1] + insert + text[brace + 1:]

# On load, reinstall the natural target stack for already-migrated constructed golems
# before their first AI tick. This does not clear legitimate vanilla anger state.
needle = '''\t\treadContainer(tag);
\t\tif (isBedrockGolem()) {'''
replacement = '''\t\treadContainer(tag);
\t\tif (!isBedrockGolem() && this.getTags().contains(CONSTRUCTED_NATURAL_AI_TAG)) {
\t\t\tthis.removeTag(NEUTRAL_CONSTRUCTED_TAG);
\t\t\tthis.constructedVillageTargetingActive = false;
\t\t\tthis.setPlayerCreated(false);
\t\t\tconfigureBedrockNaturalIronGolemTargeting();
\t\t}
\t\tif (isBedrockGolem()) {'''
if text.count(needle) != 1:
    raise SystemExit(f'Expected one readContainer load hook, found {text.count(needle)}')
text = text.replace(needle, replacement, 1)

# Sanity assertions: the natural stack must include all vanilla target goals, new
# constructed golems must never enter PlayerCreated=true semantics, and the legacy
# Villager exclusion must be gone so DefendVillageTargetGoal can see villagers.
mark_start = text.index('\tpublic void markConstructedNeutral() {')
mark_end = text.index('\n\tprivate ', mark_start)
mark_body = text[mark_start:mark_end]
if 'setPlayerCreated(true)' in mark_body:
    raise SystemExit('Constructed golem still becomes PlayerCreated=true')
can_attack_start = text.index('public boolean canAttackType')
can_attack_end = text.find('\n\t@Override', can_attack_start + 1)
if can_attack_end < 0:
    can_attack_end = can_attack_start + 1200
if 'type == EntityType.VILLAGER' in text[can_attack_start:can_attack_end]:
    raise SystemExit('Villager canAttackType exclusion still present')
for token in ('DefendVillageTargetGoal', 'HurtByTargetGoal', 'NearestAttackableTargetGoal', 'ResetUniversalAngerTargetGoal'):
    if token not in text:
        raise SystemExit(f'Missing vanilla target goal: {token}')

p.write_text(text)
print('Applied permanent natural Iron Golem target AI and fixed village reputation visibility for all T-built Extra Golems.')
