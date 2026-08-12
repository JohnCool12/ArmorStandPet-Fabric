from pathlib import Path

ROOT = Path("project")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one match in {path} but found {count}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1))


# T-constructed Extra Golems must NOT masquerade as naturally spawned village golems.
# Keep vanilla's player-created bit (which prevents village reputation spillover), then
# layer a separate direct-retaliation neutral mode on top.
head = ROOT / "src/main/java/com/mcmoddev/golems/block/GolemHeadBlock.java"
replace_once(
    head,
    "\t\t\t\t// Extra Golems built from the T-shaped block structure should behave like\n"
    "\t\t\t\t// naturally spawned (neutral) Iron Golems, not player-created passive ones.\n"
    "\t\t\t\tgolem.setPlayerCreated(false);",
    "\t\t\t\t// Keep vanilla's player-built flag so village reputation cannot make nearby\n"
    "\t\t\t\t// Extra Golems share aggression. A separate direct-retaliation mode makes\n"
    "\t\t\t\t// this specific constructed golem neutral instead of passive.\n"
    "\t\t\t\tgolem.markConstructedNeutral();",
)

golem = ROOT / "src/main/java/com/mcmoddev/golems/entity/GolemBase.java"

# Target-goal imports for the constructed-neutral target selector.
replace_once(
    golem,
    "import net.minecraft.world.entity.ai.goal.FloatGoal;\n",
    "import net.minecraft.world.entity.ai.goal.FloatGoal;\n"
    "import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;\n"
    "import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;\n",
)
replace_once(
    golem,
    "import net.minecraft.world.entity.item.ItemEntity;\n",
    "import net.minecraft.world.entity.item.ItemEntity;\n"
    "import net.minecraft.world.entity.monster.Creeper;\n"
    "import net.minecraft.world.entity.monster.Enemy;\n",
)

# Persistent marker. Entity scoreboard tags are saved by vanilla Entity NBT, so this
# survives world saves without another custom data serializer.
replace_once(
    golem,
    '\tprivate static final String KEY_CHILD = "IsChild";\n',
    '\tprivate static final String KEY_CHILD = "IsChild";\n'
    '\tprivate static final String NEUTRAL_CONSTRUCTED_TAG = "extra_golems_neutral_constructed";\n',
)

# When a neutral T-built golem is directly retaliating, player attack type becomes
# valid. At all other times the vanilla player-created protection remains in force.
replace_once(
    golem,
    "\t\tif (type == EntityType.PLAYER && this.isPlayerCreated()) {\n"
    "\t\t\t// Bedrock golems must be able to retaliate against a player who actually\n"
    "\t\t\t// attacks them, even though mod-built golems are marked PlayerCreated.\n"
    "\t\t\tif (isBedrockGolem()) return true;\n"
    "\t\t\treturn ExtraGolems.CONFIG.enableFriendlyFire();\n"
    "\t\t}",
    "\t\tif (type == EntityType.PLAYER && this.isPlayerCreated()) {\n"
    "\t\t\t// A constructed-neutral golem may attack a player only while that player\n"
    "\t\t\t// is its direct last attacker. This keeps retaliation individual rather\n"
    "\t\t\t// than allowing village reputation to select unrelated players.\n"
    "\t\t\tif (isConstructedNeutral()) return this.getLastHurtByMob() instanceof Player;\n"
    "\t\t\t// Non-constructed Bedrock retains its explicit provocation behavior.\n"
    "\t\t\tif (isBedrockGolem()) return true;\n"
    "\t\t\treturn ExtraGolems.CONFIG.enableFriendlyFire();\n"
    "\t\t}",
)

# Direct-neutral helpers. The target selector deliberately omits DefendVillageTargetGoal
# and the persistent-angry-player NearestAttackableTargetGoal. That prevents one golem's
# fight/village reputation from recruiting another Extra Golem or re-acquiring a player
# after the original retaliation has ended.
marker = "\tprivate boolean isBedrockGolem() {\n"
helpers = r'''\tprivate boolean isConstructedNeutral() {
\t\treturn this.getTags().contains(NEUTRAL_CONSTRUCTED_TAG);
\t}

\t/**
\t * Marks a T-shape/pumpkin-built Extra Golem as individually neutral toward players.
\t * Vanilla's PlayerCreated flag stays true to suppress village-wide player hostility;
\t * direct retaliation is supplied by HurtByTargetGoal plus the temporary last attacker.
\t */
\tpublic void markConstructedNeutral() {
\t\tthis.addTag(NEUTRAL_CONSTRUCTED_TAG);
\t\tthis.setPlayerCreated(true);
\t\tthis.stopBeingAngry();
\t\tthis.setLastHurtByMob(null);
\t\tif (this.getTarget() instanceof Player) {
\t\t\tthis.setTarget(null);
\t\t}
\t\tconfigureConstructedNeutralTargeting();
\t}

\tprivate void configureConstructedNeutralTargeting() {
\t\tthis.targetSelector.getAvailableGoals().clear();
\t\t// Direct attacker only. HurtByTargetGoal does not call for help unless
\t\t// setAlertOthers() is explicitly enabled, which vanilla Iron Golem does not do.
\t\tthis.targetSelector.addGoal(2, new HurtByTargetGoal(this));
\t\t// Preserve vanilla Iron Golem automatic hostility toward hostile mobs (except
\t\t// Creepers), while deliberately omitting village/player-reputation target goals.
\t\tthis.targetSelector.addGoal(3, new NearestAttackableTargetGoal<>(this, Mob.class, 5, false, false,
\t\t\t\tentity -> entity instanceof Enemy && !(entity instanceof Creeper)));
\t}

\tprivate void maintainConstructedNeutralRetaliation() {
\t\tif (!isConstructedNeutral()) {
\t\t\treturn;
\t\t}

\t\t// Persistent anger is what allows an Iron Golem to reacquire a player later.
\t\t// T-built Extra Golems use one retaliation episode only, so strip that state.
\t\tif (this.getPersistentAngerTarget() != null || this.getRemainingPersistentAngerTime() != 0) {
\t\t\tthis.setPersistentAngerTarget(null);
\t\t\tthis.setRemainingPersistentAngerTime(0);
\t\t}

\t\tfinal LivingEntity lastAttacker = this.getLastHurtByMob();
\t\tfinal LivingEntity currentTarget = this.getTarget();
\t\tif (lastAttacker instanceof Player player) {
\t\t\tfinal double followDistance = this.getAttributeValue(Attributes.FOLLOW_RANGE);
\t\t\tfinal boolean validRetaliation = currentTarget == player
\t\t\t\t\t&& player.isAlive()
\t\t\t\t\t&& !player.isCreative()
\t\t\t\t\t&& !player.isSpectator()
\t\t\t\t\t&& this.distanceToSqr(player) <= followDistance * followDistance;
\t\t\tif (!validRetaliation) {
\t\t\t\tif (currentTarget instanceof Player) {
\t\t\t\t\tthis.setTarget(null);
\t\t\t\t}
\t\t\t\t// Clearing lastHurtByMob prevents HurtByTargetGoal from starting again
\t\t\t\t// when the same player later walks back into range or respawns.
\t\t\t\tthis.setLastHurtByMob(null);
\t\t\t}
\t\t} else if (currentTarget instanceof Player) {
\t\t\t// No direct player attacker exists: never inherit/reputation-select a player.
\t\t\tthis.setTarget(null);
\t\t}
\t}

'''.replace('\\t', '\t')
replace_once(golem, marker, helpers + marker)

# Run the strict-neutral cleanup every server AI tick, after vanilla updates its anger.
replace_once(
    golem,
    "\tpublic void customServerAiStep() {\n\t\tsuper.customServerAiStep();\n",
    "\tpublic void customServerAiStep() {\n\t\tsuper.customServerAiStep();\n"
    "\t\tmaintainConstructedNeutralRetaliation();\n",
)

# On load, re-apply the custom target selector. Also migrate a currently-angry legacy
# T-built golem from the immediately previous custom build: that build stored
# PlayerCreated=false but had no construction marker. A saved persistent player anger
# target is a safe signal to clear the old sticky state and move it to the new model.
replace_once(
    golem,
    "\t\treadContainer(tag);\n\t\treadVariant(tag);\n",
    "\t\treadContainer(tag);\n"
    "\t\tif (!isConstructedNeutral() && !this.isPlayerCreated() && this.getPersistentAngerTarget() != null) {\n"
    "\t\t\tthis.addTag(NEUTRAL_CONSTRUCTED_TAG);\n"
    "\t\t\tthis.setPlayerCreated(true);\n"
    "\t\t\tthis.setPersistentAngerTarget(null);\n"
    "\t\t\tthis.setRemainingPersistentAngerTime(0);\n"
    "\t\t\tthis.setLastHurtByMob(null);\n"
    "\t\t\tif (this.getTarget() instanceof Player) this.setTarget(null);\n"
    "\t\t}\n"
    "\t\tif (isConstructedNeutral()) {\n"
    "\t\t\tconfigureConstructedNeutralTargeting();\n"
    "\t\t}\n"
    "\t\treadVariant(tag);\n",
)

# Replace the Bedrock-only provocation method with a combined implementation:
# constructed-neutral player hits are direct/local for every Extra Golem; Bedrock still
# registers otherwise-ignored attempted hits from mobs and non-constructed players.
old_hurt = r'''\t@Override
\tpublic boolean hurt(final DamageSource source, final float amount) {
\t\tif (!this.level().isClientSide() && isBedrockGolem()) {
\t\t\tfinal Entity sourceEntity = source.getEntity();
\t\t\tif (sourceEntity instanceof LivingEntity attacker && attacker != this && attacker.isAlive()) {
\t\t\t\t// Creative/spectator players remain invalid combat targets, matching
\t\t\t\t// normal vanilla targeting expectations.
\t\t\t\tif (!(attacker instanceof Player player) || (!player.isCreative() && !player.isSpectator())) {
\t\t\t\t\t// HurtByTargetGoal normally receives this state from LivingEntity#hurt,
\t\t\t\t\t// but Bedrock's damage immunity returns before vanilla can set it.
\t\t\t\t\tthis.setLastHurtByMob(attacker);
\t\t\t\t\tthis.setTarget(attacker);

\t\t\t\t\t// Iron golems use persistent anger for players. Preserve that behavior
\t\t\t\t\t// so the Bedrock golem remembers and pursues the provoking player.
\t\t\t\t\tif (attacker instanceof Player player) {
\t\t\t\t\t\tthis.setPersistentAngerTarget(player.getUUID());
\t\t\t\t\t\tthis.startPersistentAngerTimer();
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t}

\t\t// For Bedrock this reaches isInvulnerableTo() and returns false before
\t\t// health loss, hurtTime, knockback, hurt sound, or the red damage flash.
\t\treturn super.hurt(source, amount);
\t}
'''.replace('\\t', '\t')
new_hurt = r'''\t@Override
\tpublic boolean hurt(final DamageSource source, final float amount) {
\t\tif (!this.level().isClientSide()) {
\t\t\tfinal Entity sourceEntity = source.getEntity();

\t\t\t// Strict individual neutrality for T-built Extra Golems. Only this golem
\t\t\t// records the player who actually hit it; nearby golems receive no state.
\t\t\tif (isConstructedNeutral() && sourceEntity instanceof Player player
\t\t\t\t\t&& !player.isCreative() && !player.isSpectator()) {
\t\t\t\tthis.setPersistentAngerTarget(null);
\t\t\t\tthis.setRemainingPersistentAngerTime(0);
\t\t\t\tthis.setLastHurtByMob(player);
\t\t\t\tthis.setTarget(player);
\t\t\t}

\t\t\tif (isBedrockGolem() && sourceEntity instanceof LivingEntity attacker
\t\t\t\t\t&& attacker != this && attacker.isAlive()) {
\t\t\t\t// Creative/spectator players remain invalid combat targets.
\t\t\t\tif (!(attacker instanceof Player player) || (!player.isCreative() && !player.isSpectator())) {
\t\t\t\t\t// Constructed-neutral player provocation was already registered above.
\t\t\t\t\t// Other Bedrock attack attempts still need explicit bookkeeping because
\t\t\t\t\t// invulnerability prevents vanilla LivingEntity#hurt from doing it.
\t\t\t\t\tif (!(attacker instanceof Player) || !isConstructedNeutral()) {
\t\t\t\t\t\tthis.setLastHurtByMob(attacker);
\t\t\t\t\t\tthis.setTarget(attacker);
\t\t\t\t\t}

\t\t\t\t\t// Preserve the earlier persistent Bedrock behavior only for Bedrock
\t\t\t\t\t// golems that were NOT built under the new strict-neutral construction mode.
\t\t\t\t\tif (attacker instanceof Player player && !isConstructedNeutral()) {
\t\t\t\t\t\tthis.setPersistentAngerTarget(player.getUUID());
\t\t\t\t\t\tthis.startPersistentAngerTimer();
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t}

\t\t// Bedrock still exits through isInvulnerableTo() before health loss, hurtTime,
\t\t// knockback, hurt sound, or the red damage flash.
\t\treturn super.hurt(source, amount);
\t}
'''.replace('\\t', '\t')
replace_once(golem, old_hurt, new_hurt)

# Carry forward the most recent zero-knockback resource-only edits into code-built JARs.
sculk = ROOT / "src/main/resources/data/golems/golems/golem/sculk_catalyst.json"
replace_once(sculk, '\t"armor": 2.0,\n\t"immune": [', '\t"armor": 2.0,\n\t"knockback_resistance": 1.0,\n\t"immune": [')
for name in ("obsidian", "crying_obsidian"):
    p = ROOT / f"src/main/resources/data/golems/golems/golem/{name}.json"
    replace_once(p, '"knockback_resistance": 0.8', '"knockback_resistance": 1.0')

# Ancient Debris is already 1.0 upstream; assert it remains so.
ancient = (ROOT / "src/main/resources/data/golems/golems/golem/ancient_debris.json").read_text()
if '"knockback_resistance": 1.0' not in ancient:
    raise SystemExit("Ancient Debris lost full knockback resistance")

print("Applied strict individual neutral retaliation and expanded zero-knockback settings.")
