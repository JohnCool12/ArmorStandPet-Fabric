from pathlib import Path

p = Path("project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java")
text = p.read_text()


def replace_method(signature: str, replacement: str) -> None:
    global text
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f"Missing method signature: {signature}")
    if text.find(signature, start + 1) >= 0:
        raise SystemExit(f"Duplicate method signature: {signature}")
    brace = text.find("{", start)
    if brace < 0:
        raise SystemExit(f"Missing opening brace for: {signature}")
    depth = 0
    end = None
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise SystemExit(f"Missing closing brace for: {signature}")
    text = text[:start] + replacement + text[end:]


# Bedrock must never participate in the custom constructed-neutral/hybrid system.
# It is a natural Iron Golem from the target AI's perspective everywhere.
replace_method(
    "\tprivate boolean isConstructedNeutral() {",
    '''\tprivate boolean isConstructedNeutral() {
\t\treturn !isBedrockGolem() && this.getTags().contains(NEUTRAL_CONSTRUCTED_TAG);
\t}''',
)

# T-shape construction still calls this method for all Extra Golems. For Bedrock,
# explicitly choose natural-Iron-Golem semantics and do NOT add the constructed marker.
replace_method(
    "\tpublic void markConstructedNeutral() {",
    '''\tpublic void markConstructedNeutral() {
\t\tif (isBedrockGolem()) {
\t\t\tthis.removeTag(NEUTRAL_CONSTRUCTED_TAG);
\t\t\tthis.constructedVillageTargetingActive = false;
\t\t\tthis.setPlayerCreated(false);
\t\t\tconfigureBedrockNaturalTargeting();
\t\t\treturn;
\t\t}

\t\tthis.addTag(NEUTRAL_CONSTRUCTED_TAG);
\t\tthis.constructedVillageTargetingActive = false;
\t\tthis.setPlayerCreated(true);
\t\tthis.stopBeingAngry();
\t\tthis.setLastHurtByMob(null);
\t\tif (this.getTarget() instanceof Player) {
\t\t\tthis.setTarget(null);
\t\t}
\t\tconfigureConstructedNeutralTargeting();
\t}''',
)

# Install the target priorities used by a natural vanilla Iron Golem. This selector is
# stable for Bedrock's whole lifetime: no village boundary ever clears/rebuilds it.
marker = "\tprivate boolean isBedrockGolem() {\n"
helper = '''\tprivate void configureBedrockNaturalTargeting() {
\t\tthis.targetSelector.getAvailableGoals().clear();
\t\tthis.targetSelector.addGoal(1, new DefendVillageTargetGoal(this));
\t\tthis.targetSelector.addGoal(2, new HurtByTargetGoal(this));
\t\tthis.targetSelector.addGoal(3, new NearestAttackableTargetGoal<>(this, Player.class, 10, true, false,
\t\t\t\tthis::isAngryAt));
\t\tthis.targetSelector.addGoal(3, new NearestAttackableTargetGoal<>(this, Mob.class, 5, false, false,
\t\t\t\tentity -> entity instanceof Enemy && !(entity instanceof Creeper)));
\t\tthis.targetSelector.addGoal(4, new ResetUniversalAngerTargetGoal<>(this, false));
\t}

'''
if text.count(marker) != 1:
    raise SystemExit(f"Expected one isBedrockGolem marker, found {text.count(marker)}")
text = text.replace(marker, helper + marker, 1)

# Bump migration once more. Existing Bedrock entities may contain tags/playerCreated
# state from strict/hybrid builds. Reset transient combat state once, remove the custom
# construction marker, install the natural selector, then never rebuild it again.
old_tag = 'private static final String BEDROCK_NATURAL_HOSTILITY_TAG = "extra_golems_bedrock_natural_hostility_v3_stable_village";'
new_tag = 'private static final String BEDROCK_NATURAL_HOSTILITY_TAG = "extra_golems_bedrock_natural_hostility_v4_vanilla_natural";'
if text.count(old_tag) != 1:
    raise SystemExit(f"Expected one Bedrock stable-village migration tag, found {text.count(old_tag)}")
text = text.replace(old_tag, new_tag, 1)

replace_method(
    "\tprivate void migrateBedrockNaturalHostilityState() {",
    '''\tprivate void migrateBedrockNaturalHostilityState() {
\t\tif (!isBedrockGolem()) {
\t\t\treturn;
\t\t}

\t\t// Bedrock is ALWAYS a natural Iron Golem for targeting semantics, regardless
\t\t// of construction method or village location.
\t\tthis.removeTag(NEUTRAL_CONSTRUCTED_TAG);
\t\tthis.constructedVillageTargetingActive = false;
\t\tif (this.isPlayerCreated()) {
\t\t\tthis.setPlayerCreated(false);
\t\t}

\t\tif (!this.getTags().contains(BEDROCK_NATURAL_HOSTILITY_TAG)) {
\t\t\t// One-time cleanup of stale forced targets/anger from older custom builds.
\t\t\tthis.stopBeingAngry();
\t\t\tthis.setLastHurtByMob(null);
\t\t\tthis.setTarget(null);
\t\t\tconfigureBedrockNaturalTargeting();
\t\t\tthis.addTag(BEDROCK_NATURAL_HOSTILITY_TAG);
\t\t}
\t}''',
)

# The custom constructed-neutral maintenance/mode switch must be impossible for Bedrock.
# isConstructedNeutral() already excludes it, but explicit guards make future changes safe.
for signature in (
    "\tprivate void maintainConstructedNeutralRetaliation() {",
    "\tprivate void updateConstructedNeutralTargetingMode() {",
):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f"Missing method for Bedrock guard: {signature}")
    brace = text.find("{", start)
    insertion = "\n\t\tif (isBedrockGolem()) {\n\t\t\treturn;\n\t\t}"
    # Avoid duplicate guard if rerun.
    if text.find("if (isBedrockGolem())", brace, brace + 140) < 0:
        text = text[:brace + 1] + insertion + text[brace + 1:]

# Village helper must never make Bedrock enter hybrid mode.
replace_method(
    "\tprivate boolean isConstructedNeutralInVillage() {",
    '''\tprivate boolean isConstructedNeutralInVillage() {
\t\treturn !isBedrockGolem()
\t\t\t\t&& isConstructedNeutral()
\t\t\t\t&& this.level() instanceof ServerLevel serverLevel
\t\t\t\t&& serverLevel.isVillage(this.blockPosition());
\t}''',
)

# Bedrock's invulnerability prevents vanilla LivingEntity#hurt from writing the direct
# attacker. Preserve ONLY that missing stimulus. Target selection, pursuit, anger,
# village reputation, hostile-mob scanning, and abandonment are all left to the natural
# Iron Golem target goals above.
hurt_sig = "\t@Override\n\tpublic boolean hurt(final DamageSource source, final float amount) {"
hurt_start = text.find(hurt_sig)
if hurt_start < 0:
    raise SystemExit("Missing hurt override")
hurt_brace = text.find("{", hurt_start)
depth = 0
hurt_end = None
for i in range(hurt_brace, len(text)):
    if text[i] == "{": depth += 1
    elif text[i] == "}":
        depth -= 1
        if depth == 0:
            hurt_end = i + 1
            break
if hurt_end is None:
    raise SystemExit("Could not find hurt method end")
new_hurt = '''\t@Override
\tpublic boolean hurt(final DamageSource source, final float amount) {
\t\tif (!this.level().isClientSide() && isBedrockGolem()) {
\t\t\tfinal Entity sourceEntity = source.getEntity();
\t\t\tif (sourceEntity instanceof LivingEntity attacker && attacker != this && attacker.isAlive()) {
\t\t\t\tif (!(attacker instanceof Player player) || (!player.isCreative() && !player.isSpectator())) {
\t\t\t\t\t// This is the ONLY Bedrock-specific hostility bridge. Do not force a target
\t\t\t\t\t// and do not synthesize persistent anger; HurtByTargetGoal and NeutralMob
\t\t\t\t\t// bookkeeping decide the response exactly like a natural Iron Golem.
\t\t\t\t\tthis.setLastHurtByMob(attacker);
\t\t\t\t}
\t\t\t}
\t\t}

\t\t// Bedrock reaches isInvulnerableTo() and exits before health loss, hurtTime,
\t\t// knockback, hurt sound, or the red damage flash.
\t\treturn super.hurt(source, amount);
\t}'''
text = text[:hurt_start] + new_hurt + text[hurt_end:]

# Static safety assertions for the final architecture.
assert '!isBedrockGolem() && this.getTags().contains(NEUTRAL_CONSTRUCTED_TAG)' in text
assert 'extra_golems_bedrock_natural_hostility_v4_vanilla_natural' in text
assert 'private void configureBedrockNaturalTargeting()' in text
assert 'new DefendVillageTargetGoal(this)' in text
assert 'new HurtByTargetGoal(this)' in text
assert 'this::isAngryAt' in text
assert 'entity instanceof Enemy && !(entity instanceof Creeper)' in text
assert 'new ResetUniversalAngerTargetGoal' in text

hs = text.index(hurt_sig)
he = text.index('\n\t@Override', hs + len(hurt_sig)) if '\n\t@Override' in text[hs + len(hurt_sig):] else len(text)
hb = text[hs:he]
assert 'this.setLastHurtByMob(attacker);' in hb
assert 'this.setTarget(attacker);' not in hb
assert 'startPersistentAngerTimer' not in hb

p.write_text(text)
print("Applied permanent vanilla-natural Iron Golem targeting semantics to Bedrock.")
