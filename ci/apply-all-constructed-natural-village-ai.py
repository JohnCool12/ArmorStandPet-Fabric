from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
text = p.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Expected exactly one {label} match, found {count}')
    text = text.replace(old, new, 1)


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
        raise SystemExit(f'Missing closing brace for: {signature}')
    text = text[:start] + replacement + text[end:]


# Persistently identify T-built Extra Golems that now use the *natural* Iron Golem
# targeting semantics. This replaces the previous custom strict/hybrid neutrality tag.
replace_once(
    '\tprivate static final String NEUTRAL_CONSTRUCTED_TAG = "extra_golems_neutral_constructed";\n',
    '\tprivate static final String NEUTRAL_CONSTRUCTED_TAG = "extra_golems_neutral_constructed";\n'
    '\tprivate static final String NATURAL_CONSTRUCTED_TAG = "extra_golems_natural_constructed_v1";\n',
    'natural constructed marker',
)

# The Bedrock helper already contains the exact natural Iron Golem target stack verified by
# the previous GameTest. Generalize it so every T-built Extra Golem can use the same stack.
old_helper_sig = '\tprivate void configureBedrockNaturalIronGolemTargeting() {'
start = text.find(old_helper_sig)
if start < 0:
    raise SystemExit('Missing verified Bedrock natural target helper')
brace = text.find('{', start)
depth = 0
end = None
for i in range(brace, len(text)):
    if text[i] == '{': depth += 1
    elif text[i] == '}':
        depth -= 1
        if depth == 0:
            end = i + 1
            break
old_helper = text[start:end]
expected = [
    'new DefendVillageTargetGoal(this)',
    'new HurtByTargetGoal(this)',
    'new NearestAttackableTargetGoal<>(this, Player.class',
    'this::isAngryAt',
    'entity instanceof Enemy && !(entity instanceof Creeper)',
    'new ResetUniversalAngerTargetGoal<>(this, false)',
]
for needle in expected:
    if needle not in old_helper:
        raise SystemExit(f'Verified natural target helper is missing {needle!r}')
new_helpers = old_helper.replace(
    'private void configureBedrockNaturalIronGolemTargeting()',
    'private void configureNaturalIronGolemTargeting()',
    1,
) + '''\n\n\tprivate void configureBedrockNaturalIronGolemTargeting() {
\t\tconfigureNaturalIronGolemTargeting();
\t}'''
text = text[:start] + new_helpers + text[end:]

# T-shaped/pumpkin construction now means natural Iron Golem semantics for EVERY Extra
# Golem. DefendVillageTargetGoal itself decides when village reputation is relevant; there
# is no custom village/outside-village target-selector mode and no player-created immunity.
replace_method(
    '\tpublic void markConstructedNeutral() {',
    '''\tpublic void markConstructedNeutral() {
\t\tthis.removeTag(NEUTRAL_CONSTRUCTED_TAG);
\t\tthis.addTag(NATURAL_CONSTRUCTED_TAG);
\t\tthis.constructedVillageTargetingActive = false;
\t\tthis.setPlayerCreated(false);
\t\tthis.stopBeingAngry();
\t\tthis.setLastHurtByMob(null);
\t\tthis.setTarget(null);
\t\tconfigureNaturalIronGolemTargeting();
\t\tif (isBedrockGolem()) {
\t\t\tthis.addTag(BEDROCK_NATURAL_HOSTILITY_TAG);
\t\t}
\t}''',
)

# The legacy runtime heuristic used to convert any non-player-created Extra Golem involved
# in a player fight back into the custom strict-neutral model. Exclude the new natural
# construction marker so legitimate vanilla retaliation/reputation can never downgrade it.
legacy = '''\t\tif (!isBedrockGolem() && !isConstructedNeutral() && !this.isPlayerCreated()
\t\t\t\t&& (this.getLastHurtByMob() instanceof Player || this.getTarget() instanceof Player)) {'''
legacy_new = '''\t\tif (!isBedrockGolem() && !this.getTags().contains(NATURAL_CONSTRUCTED_TAG)
\t\t\t\t&& !isConstructedNeutral() && !this.isPlayerCreated()
\t\t\t\t&& (this.getLastHurtByMob() instanceof Player || this.getTarget() instanceof Player)) {'''
replace_once(legacy, legacy_new, 'runtime legacy migration guard')

# Migrate old T-built Extra Golems from the previous strict/hybrid builds on NBT load.
# Also protect already-migrated natural golems from the old persistent-anger heuristic.
needle = '\t\treadContainer(tag);\n'
insert = '''\t\treadContainer(tag);
\t\tif (!isBedrockGolem() && this.getTags().contains(NEUTRAL_CONSTRUCTED_TAG)) {
\t\t\t// One-time conversion of an existing T-built golem from the old custom
\t\t\t// strict/hybrid neutrality model to real natural Iron Golem semantics.
\t\t\tthis.removeTag(NEUTRAL_CONSTRUCTED_TAG);
\t\t\tthis.addTag(NATURAL_CONSTRUCTED_TAG);
\t\t\tthis.constructedVillageTargetingActive = false;
\t\t\tthis.setPlayerCreated(false);
\t\t\tthis.stopBeingAngry();
\t\t\tthis.setLastHurtByMob(null);
\t\t\tthis.setTarget(null);
\t\t\tconfigureNaturalIronGolemTargeting();
\t\t}
\t\tif (!isBedrockGolem() && this.getTags().contains(NATURAL_CONSTRUCTED_TAG)) {
\t\t\tthis.removeTag(NEUTRAL_CONSTRUCTED_TAG);
\t\t\tthis.constructedVillageTargetingActive = false;
\t\t\tthis.setPlayerCreated(false);
\t\t\tconfigureNaturalIronGolemTargeting();
\t\t}
'''
replace_once(needle, insert, 'readContainer migration insertion')

# Prevent the old NBT compatibility heuristic from converting a valid natural-constructed
# golem back to PlayerCreated=true merely because it has legitimate vanilla persistent anger.
old_load_guard = '''\t\t\tif (!isConstructedNeutral() && !this.isPlayerCreated() && this.getPersistentAngerTarget() != null) {'''
new_load_guard = '''\t\t\tif (!this.getTags().contains(NATURAL_CONSTRUCTED_TAG)
\t\t\t\t\t&& !isConstructedNeutral() && !this.isPlayerCreated()
\t\t\t\t\t&& this.getPersistentAngerTarget() != null) {'''
replace_once(old_load_guard, new_load_guard, 'NBT legacy anger guard')

# Bedrock also gets the common natural-construction marker so all T-built golems share one
# semantic baseline. Bedrock still keeps its own V4 tag solely for its invulnerability bridge.
old_bedrock_load = '''\t\tif (isBedrockGolem()) {
\t\t\tfinal boolean needsV4Migration = !this.getTags().contains(BEDROCK_NATURAL_HOSTILITY_TAG);'''
new_bedrock_load = '''\t\tif (isBedrockGolem()) {
\t\t\tthis.addTag(NATURAL_CONSTRUCTED_TAG);
\t\t\tfinal boolean needsV4Migration = !this.getTags().contains(BEDROCK_NATURAL_HOSTILITY_TAG);'''
replace_once(old_bedrock_load, new_bedrock_load, 'Bedrock common natural marker')

# Source-level invariants.
if 'configureNaturalIronGolemTargeting();' not in text:
    raise SystemExit('Generic natural Iron Golem target helper is unused')
if 'this.addTag(NATURAL_CONSTRUCTED_TAG);' not in text:
    raise SystemExit('Natural constructed marker is never applied')
if 'this.setPlayerCreated(false);' not in text:
    raise SystemExit('Natural constructed golems are not PlayerCreated=false')

p.write_text(text)
print('Applied true natural Iron Golem village/reputation targeting to all T-built Extra Golems.')
