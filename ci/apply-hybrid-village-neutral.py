from pathlib import Path

p = Path("project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java")
text = p.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label} match, found {count}")
    text = text.replace(old, new, 1)


# Add the two vanilla target goals that strict-neutral intentionally omitted.
replace_once(
    "import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;\n"
    "import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;\n",
    "import net.minecraft.world.entity.ai.goal.target.DefendVillageTargetGoal;\n"
    "import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;\n"
    "import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;\n"
    "import net.minecraft.world.entity.ai.goal.target.ResetUniversalAngerTargetGoal;\n",
    "target-goal import block",
)

# Track which target-selector mode is actually installed. This is deliberately transient:
# village membership is recalculated from the server's own POI/village system after load.
replace_once(
    "\tprivate static final String NEUTRAL_CONSTRUCTED_TAG = \"extra_golems_neutral_constructed\";\n",
    "\tprivate static final String NEUTRAL_CONSTRUCTED_TAG = \"extra_golems_neutral_constructed\";\n"
    "\tprivate boolean constructedVillageTargetingActive;\n",
    "constructed neutral marker",
)

# Clarify the construction comment: individual neutrality is the default, but village
# association dynamically enables the vanilla-natural reputation target selector.
replace_once(
    "\t * Marks a T-shape/pumpkin-built Extra Golem as individually neutral toward players.\n"
    "\t * Vanilla's PlayerCreated flag stays true to suppress village-wide player hostility;\n"
    "\t * direct retaliation is supplied by HurtByTargetGoal plus the temporary last attacker.\n",
    "\t * Marks a T-shape/pumpkin-built Extra Golem as neutral toward players. Outside a\n"
    "\t * village it uses direct individual retaliation; while inside a real Minecraft\n"
    "\t * village it dynamically switches to the same reputation-aware target goals used\n"
    "\t * by a naturally spawned vanilla Iron Golem.\n",
    "markConstructedNeutral javadoc",
)
replace_once(
    "\t\tthis.addTag(NEUTRAL_CONSTRUCTED_TAG);\n"
    "\t\tthis.setPlayerCreated(true);\n",
    "\t\tthis.addTag(NEUTRAL_CONSTRUCTED_TAG);\n"
    "\t\tthis.constructedVillageTargetingActive = false;\n"
    "\t\tthis.setPlayerCreated(true);\n",
    "markConstructedNeutral initialization",
)

# Insert the hybrid village mode directly before the strict target-selector method.
marker = "\tprivate void configureConstructedNeutralTargeting() {\n"
helpers = '''\tprivate boolean isConstructedNeutralInVillage() {
\t\treturn isConstructedNeutral()
\t\t\t\t&& this.level() instanceof ServerLevel serverLevel
\t\t\t\t&& serverLevel.isVillage(this.blockPosition());
\t}

\t/**
\t * Target selector copied from vanilla IronGolem's natural/reputation-aware target
\t * set: defend villagers/reputation, retaliate against a direct attacker, reacquire
\t * the persistent anger player, attack hostile mobs except creepers, and honor the
\t * universal-anger gamerule reset behavior. Movement goals remain the inherited
\t * IronGolem goals, so only player-target selection changes between the two modes.
\t */
\tprivate void configureConstructedVillageTargeting() {
\t\tthis.targetSelector.getAvailableGoals().clear();
\t\tthis.targetSelector.addGoal(1, new DefendVillageTargetGoal(this));
\t\tthis.targetSelector.addGoal(2, new HurtByTargetGoal(this));
\t\tthis.targetSelector.addGoal(3, new NearestAttackableTargetGoal<>(this, Player.class, 10, true, false,
\t\t\t\tthis::isAngryAt));
\t\tthis.targetSelector.addGoal(3, new NearestAttackableTargetGoal<>(this, Mob.class, 5, false, false,
\t\t\t\tentity -> entity instanceof Enemy && !(entity instanceof Creeper)));
\t\tthis.targetSelector.addGoal(4, new ResetUniversalAngerTargetGoal<>(this, false));
\t}

\tprivate void updateConstructedNeutralTargetingMode() {
\t\tif (!isConstructedNeutral()) {
\t\t\treturn;
\t\t}

\t\tfinal boolean inVillage = isConstructedNeutralInVillage();
\t\tif (inVillage) {
\t\t\t// A natural Iron Golem is PlayerCreated=false. DefendVillageTargetGoal and
\t\t\t// normal player reputation hostility therefore become available only here.
\t\t\tif (!this.constructedVillageTargetingActive || this.isPlayerCreated()) {
\t\t\t\tthis.constructedVillageTargetingActive = true;
\t\t\t\tthis.setPlayerCreated(false);
\t\t\t\tconfigureConstructedVillageTargeting();
\t\t\t}
\t\t} else {
\t\t\t// Outside village bounds, return to the strict per-entity neutral behavior.
\t\t\t// Player hostility acquired through village reputation must not leak outside.
\t\t\tif (this.constructedVillageTargetingActive || !this.isPlayerCreated()) {
\t\t\t\tthis.constructedVillageTargetingActive = false;
\t\t\t\tthis.setPlayerCreated(true);
\t\t\t\tthis.stopBeingAngry();
\t\t\t\tif (this.getTarget() instanceof Player) {
\t\t\t\t\tthis.setTarget(null);
\t\t\t\t}
\t\t\t\tif (this.getLastHurtByMob() instanceof Player) {
\t\t\t\t\tthis.setLastHurtByMob(null);
\t\t\t\t}
\t\t\t\tconfigureConstructedNeutralTargeting();
\t\t\t}
\t\t}
\t}

'''
if text.count(marker) != 1:
    raise SystemExit(f"Expected one configureConstructedNeutralTargeting marker, found {text.count(marker)}")
text = text.replace(marker, helpers + marker, 1)

# Once legacy migration has run and the golem is known to be constructed-neutral,
# install/reconcile the correct mode every tick. In village mode, do NOT execute the
# strict cleanup below: vanilla persistent anger and reputation are intentionally active.
replace_once(
    "\t\tif (!isConstructedNeutral()) {\n"
    "\t\t\treturn;\n"
    "\t\t}\n\n"
    "\t\t// Persistent anger is what allows an Iron Golem to reacquire a player later.\n",
    "\t\tif (!isConstructedNeutral()) {\n"
    "\t\t\treturn;\n"
    "\t\t}\n\n"
    "\t\tupdateConstructedNeutralTargetingMode();\n"
    "\t\tif (isConstructedNeutralInVillage()) {\n"
    "\t\t\t// Inside village bounds, let vanilla-natural reputation and persistent\n"
    "\t\t\t// anger semantics run without the outside-village cleanup below.\n"
    "\t\t\treturn;\n"
    "\t\t}\n\n"
    "\t\t// Persistent anger is what allows an Iron Golem to reacquire a player later.\n",
    "strict maintenance mode gate",
)

# Outside a village, retain the strict direct-hit bookkeeping. Inside a village, normal
# damageable golems go through vanilla IronGolem hurt bookkeeping; Bedrock is handled by
# its special no-damage provocation block below because vanilla hurt exits early there.
replace_once(
    "\t\t\tif (isConstructedNeutral() && sourceEntity instanceof Player player\n"
    "\t\t\t\t\t&& !player.isCreative() && !player.isSpectator()) {\n",
    "\t\t\tif (isConstructedNeutral() && !isConstructedNeutralInVillage()\n"
    "\t\t\t\t\t&& sourceEntity instanceof Player player\n"
    "\t\t\t\t\t&& !player.isCreative() && !player.isSpectator()) {\n",
    "strict constructed player hurt condition",
)

# Bedrock still has to synthesize the hurt bookkeeping because its damage is rejected
# before vanilla can do so. In village mode, synthesize the same persistent anger that a
# natural Iron Golem would get; outside, retain the non-persistent strict behavior.
replace_once(
    "\t\t\t\t\tif (!(attacker instanceof Player) || !isConstructedNeutral()) {\n",
    "\t\t\t\t\tif (!(attacker instanceof Player) || !isConstructedNeutral()\n"
    "\t\t\t\t\t\t\t|| isConstructedNeutralInVillage()) {\n",
    "Bedrock bookkeeping condition",
)
replace_once(
    "\t\t\t\t\tif (attacker instanceof Player player && !isConstructedNeutral()) {\n",
    "\t\t\t\t\tif (attacker instanceof Player player\n"
    "\t\t\t\t\t\t\t&& (!isConstructedNeutral() || isConstructedNeutralInVillage())) {\n",
    "Bedrock persistent anger condition",
)

p.write_text(text)
print("Applied hybrid village-natural / outside-strict neutrality.")
