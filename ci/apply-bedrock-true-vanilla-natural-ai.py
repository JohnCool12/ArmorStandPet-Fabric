from pathlib import Path

p = Path("project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java")
text = p.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label} match, found {count}")
    text = text.replace(old, new, 1)


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


# V4 changes the architecture rather than merely clearing stale anger: Bedrock no longer
# participates in the constructed-neutral/hybrid target system at all. It permanently
# uses the natural Iron Golem player-created=false semantics and vanilla target stack.
old_tag = 'private static final String BEDROCK_NATURAL_HOSTILITY_TAG = "extra_golems_bedrock_natural_hostility_v3_stable_village";'
new_tag = 'private static final String BEDROCK_NATURAL_HOSTILITY_TAG = "extra_golems_bedrock_true_vanilla_natural_ai_v4";'
replace_once(old_tag, new_tag, "Bedrock V4 migration tag")

# Install an exact natural-Iron-Golem target selector for Bedrock. This helper is called
# only at construction/load, before live AI goal execution. There is intentionally no
# village gate: a naturally spawned Iron Golem keeps this target stack everywhere; the
# DefendVillage goal itself becomes relevant only when village/reputation conditions do.
marker = "\tprivate void configureConstructedNeutralTargeting() {\n"
helper = '''\tprivate void configureBedrockNaturalIronGolemTargeting() {
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
    raise SystemExit(f"Expected one constructed selector marker, found {text.count(marker)}")
text = text.replace(marker, helper + marker, 1)

# A T-built Bedrock Golem must NOT get the custom constructed-neutral tag. Instead it is
# immediately made indistinguishable from a natural Iron Golem for target selection.
# Its only intentional gameplay difference remains Bedrock damage immunity.
replace_method(
    "\tpublic void markConstructedNeutral() {",
    '''\tpublic void markConstructedNeutral() {
\t\tif (isBedrockGolem()) {
\t\t\tthis.removeTag(NEUTRAL_CONSTRUCTED_TAG);
\t\t\tthis.constructedVillageTargetingActive = false;
\t\t\tthis.setPlayerCreated(false);
\t\t\tthis.stopBeingAngry();
\t\t\tthis.setLastHurtByMob(null);
\t\t\tthis.setTarget(null);
\t\t\tconfigureBedrockNaturalIronGolemTargeting();
\t\t\tthis.addTag(BEDROCK_NATURAL_HOSTILITY_TAG);
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

# The old compatibility heuristic converted any unmarked PlayerCreated=false Extra Golem
# involved with a player into the custom constructed-neutral model. That would destroy
# Bedrock's new natural semantics immediately after its first player fight, so exclude it.
old_legacy_condition = '''\t\tif (!isConstructedNeutral() && !this.isPlayerCreated()
\t\t\t\t&& (this.getLastHurtByMob() instanceof Player || this.getTarget() instanceof Player)) {'''
new_legacy_condition = '''\t\tif (!isBedrockGolem() && !isConstructedNeutral() && !this.isPlayerCreated()
\t\t\t\t&& (this.getLastHurtByMob() instanceof Player || this.getTarget() instanceof Player)) {'''
replace_once(old_legacy_condition, new_legacy_condition, "legacy runtime neutral migration exclusion")

# Runtime migration is now only a safety net for Bedrock entities created by nonstandard
# paths. Normal T-construction and NBT loading configure the natural selector before AI.
# Do not rebuild target goals here; just normalize the semantic flags and clear legacy
# player state once if an old live entity somehow reaches this path.
replace_method(
    "\tprivate void migrateBedrockNaturalHostilityState() {",
    '''\tprivate void migrateBedrockNaturalHostilityState() {
\t\tif (!isBedrockGolem() || this.getTags().contains(BEDROCK_NATURAL_HOSTILITY_TAG)) {
\t\t\treturn;
\t\t}

\t\tthis.removeTag(NEUTRAL_CONSTRUCTED_TAG);
\t\tthis.constructedVillageTargetingActive = false;
\t\tthis.setPlayerCreated(false);
\t\tthis.stopBeingAngry();
\t\tthis.setLastHurtByMob(null);
\t\tthis.setTarget(null);
\t\tthis.addTag(BEDROCK_NATURAL_HOSTILITY_TAG);
\t}''',
)

# On NBT load, Bedrock is normalized BEFORE the first AI tick. Existing worlds from V3
# get one clean reset of the broken transient player state, then future saves preserve
# vanilla persistent anger exactly as a natural Iron Golem would. Every load also
# reinstalls the natural target stack, but does not clear legitimate V4 anger state.
old_load = '''\t\treadContainer(tag);
\t\tif (!isConstructedNeutral() && !this.isPlayerCreated() && this.getPersistentAngerTarget() != null) {
\t\t\tthis.addTag(NEUTRAL_CONSTRUCTED_TAG);
\t\t\tthis.setPlayerCreated(true);
\t\t\tthis.setPersistentAngerTarget(null);
\t\t\tthis.setRemainingPersistentAngerTime(0);
\t\t\tthis.setLastHurtByMob(null);
\t\t\tif (this.getTarget() instanceof Player) this.setTarget(null);
\t\t}
\t\tif (isConstructedNeutral()) {
\t\t\tconfigureConstructedNeutralTargeting();
\t\t}
\t\treadVariant(tag);'''
new_load = '''\t\treadContainer(tag);
\t\tif (isBedrockGolem()) {
\t\t\tfinal boolean needsV4Migration = !this.getTags().contains(BEDROCK_NATURAL_HOSTILITY_TAG);
\t\t\tthis.removeTag(NEUTRAL_CONSTRUCTED_TAG);
\t\t\tthis.constructedVillageTargetingActive = false;
\t\t\tthis.setPlayerCreated(false);
\t\t\tif (needsV4Migration) {
\t\t\t\t// One-time cleanup for Bedrock Golems saved by the broken hybrid builds.
\t\t\t\tthis.stopBeingAngry();
\t\t\t\tthis.setLastHurtByMob(null);
\t\t\t\tthis.setTarget(null);
\t\t\t\tthis.addTag(BEDROCK_NATURAL_HOSTILITY_TAG);
\t\t\t}
\t\t\tconfigureBedrockNaturalIronGolemTargeting();
\t\t} else {
\t\t\tif (!isConstructedNeutral() && !this.isPlayerCreated() && this.getPersistentAngerTarget() != null) {
\t\t\t\tthis.addTag(NEUTRAL_CONSTRUCTED_TAG);
\t\t\t\tthis.setPlayerCreated(true);
\t\t\t\tthis.setPersistentAngerTarget(null);
\t\t\t\tthis.setRemainingPersistentAngerTime(0);
\t\t\t\tthis.setLastHurtByMob(null);
\t\t\t\tif (this.getTarget() instanceof Player) this.setTarget(null);
\t\t\t}
\t\t\tif (isConstructedNeutral()) {
\t\t\t\tconfigureConstructedNeutralTargeting();
\t\t\t}
\t\t}
\t\treadVariant(tag);'''
replace_once(old_load, new_load, "NBT load targeting migration")

# Sanity checks: Bedrock direct-hit bridge must remain minimal and the hybrid maintenance
# must be unreachable for Bedrock because the constructed-neutral tag is stripped.
if 'if (!isBedrockGolem() && !isConstructedNeutral() && !this.isPlayerCreated()' not in text:
    raise SystemExit("Bedrock exclusion from legacy neutral migration missing")
if 'configureBedrockNaturalIronGolemTargeting();' not in text:
    raise SystemExit("Bedrock natural target selector helper is not referenced")
if 'extra_golems_bedrock_true_vanilla_natural_ai_v4' not in text:
    raise SystemExit("Bedrock V4 marker missing")

hurt_start = text.index("\t@Override\n\tpublic boolean hurt(final DamageSource source, final float amount) {")
hurt_end = text.index("\n\t@Override", hurt_start + 10)
hurt_body = text[hurt_start:hurt_end]
bedrock_start = hurt_body.index("if (isBedrockGolem() && sourceEntity instanceof LivingEntity attacker")
bedrock_body = hurt_body[bedrock_start:]
if "this.setTarget(attacker);" in bedrock_body:
    raise SystemExit("Bedrock hurt bridge still force-targets attacker")
if "this.startPersistentAngerTimer();" in bedrock_body:
    raise SystemExit("Bedrock hurt bridge still manually starts persistent anger")

p.write_text(text)
print("Applied permanent vanilla-natural Iron Golem target AI to Bedrock Golems.")
