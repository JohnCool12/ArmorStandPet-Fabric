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


# Bump the Bedrock migration marker. Version 2 could already be present on worlds that
# experienced the stale GoalSelector TARGET-lock bug, so version 3 intentionally performs
# one more clean reset of transient target/anger state after upgrading.
old_tag = 'private static final String BEDROCK_NATURAL_HOSTILITY_TAG = "extra_golems_bedrock_natural_hostility_v2";'
new_tag = 'private static final String BEDROCK_NATURAL_HOSTILITY_TAG = "extra_golems_bedrock_natural_hostility_v3_stable_village";'
if text.count(old_tag) != 1:
    raise SystemExit(f"Expected one Bedrock v2 migration tag, found {text.count(old_tag)}")
text = text.replace(old_tag, new_tag, 1)

# Never swap/clear the target selector while AI goals may be running. GoalSelector keeps
# control-flag locks separately from the available-goal set; deleting a running target
# goal can therefore orphan the TARGET lock and prevent every subsequently-added target
# goal (including hostile-mob scanning) from starting. Install one stable selector and
# gate only the village-specific goals by real village membership.
stable_selector = '''\tprivate void configureConstructedNeutralTargeting() {
\t\tthis.targetSelector.getAvailableGoals().clear();

\t\t// Same priority as a natural Iron Golem, but only eligible while this constructed
\t\t// Extra Golem is actually inside Minecraft's village bounds.
\t\tthis.targetSelector.addGoal(1, new DefendVillageTargetGoal(this) {
\t\t\t@Override
\t\t\tpublic boolean canUse() {
\t\t\t\treturn isConstructedNeutralInVillage() && super.canUse();
\t\t\t}

\t\t\t@Override
\t\t\tpublic boolean canContinueToUse() {
\t\t\t\treturn isConstructedNeutralInVillage() && super.canContinueToUse();
\t\t\t}
\t\t});

\t\t// Direct retaliation is valid both inside and outside villages. For Bedrock,
\t\t// hurt() synthesizes only setLastHurtByMob because the actual damage is rejected.
\t\tthis.targetSelector.addGoal(2, new HurtByTargetGoal(this));

\t\t// Persistent angry-player reacquisition is natural-Iron-Golem behavior only while
\t\t// village reputation/anger mechanics are active.
\t\tthis.targetSelector.addGoal(3, new NearestAttackableTargetGoal<Player>(this, Player.class, 10, true, false,
\t\t\t\tthis::isAngryAt) {
\t\t\t@Override
\t\t\tpublic boolean canUse() {
\t\t\t\treturn isConstructedNeutralInVillage() && super.canUse();
\t\t\t}

\t\t\t@Override
\t\t\tpublic boolean canContinueToUse() {
\t\t\t\treturn isConstructedNeutralInVillage() && super.canContinueToUse();
\t\t\t}
\t\t});

\t\t// Always retain the vanilla Iron Golem monster scan. This goal is deliberately
\t\t// never removed during a player fight or a village-boundary transition.
\t\tthis.targetSelector.addGoal(3, new NearestAttackableTargetGoal<>(this, Mob.class, 5, false, false,
\t\t\t\tentity -> entity instanceof Enemy && !(entity instanceof Creeper)));

\t\tthis.targetSelector.addGoal(4, new ResetUniversalAngerTargetGoal<GolemBase>(this, false) {
\t\t\t@Override
\t\t\tpublic boolean canUse() {
\t\t\t\treturn isConstructedNeutralInVillage() && super.canUse();
\t\t\t}
\t\t});
\t}'''
replace_method("\tprivate void configureConstructedNeutralTargeting() {", stable_selector)

# Keep the old helper name as a harmless alias for compatibility with the cumulative
# patch chain, but it is no longer called during live mode changes.
replace_method(
    "\tprivate void configureConstructedVillageTargeting() {",
    '''\tprivate void configureConstructedVillageTargeting() {
\t\tconfigureConstructedNeutralTargeting();
\t}''',
)

# Village transitions now change only the PlayerCreated semantic bit and player-derived
# state. The selector itself remains stable, so there is no opportunity to orphan a
# running TARGET lock. Do not call stopBeingAngry() here: that method also clears a live
# hostile-mob target, which is precisely the behavior we want to preserve.
replace_method(
    "\tprivate void updateConstructedNeutralTargetingMode() {",
    '''\tprivate void updateConstructedNeutralTargetingMode() {
\t\tif (!isConstructedNeutral()) {
\t\t\treturn;
\t\t}

\t\tfinal boolean inVillage = isConstructedNeutralInVillage();
\t\tif (inVillage) {
\t\t\tthis.constructedVillageTargetingActive = true;
\t\t\tif (this.isPlayerCreated()) {
\t\t\t\t// Natural village Iron Golems are PlayerCreated=false, which enables
\t\t\t\t// DefendVillage/reputation semantics and ordinary neutral anger behavior.
\t\t\t\tthis.setPlayerCreated(false);
\t\t\t}
\t\t} else {
\t\t\tfinal boolean wasVillageMode = this.constructedVillageTargetingActive || !this.isPlayerCreated();
\t\t\tthis.constructedVillageTargetingActive = false;
\t\t\tif (!this.isPlayerCreated()) {
\t\t\t\tthis.setPlayerCreated(true);
\t\t\t}

\t\t\tif (wasVillageMode) {
\t\t\t\t// Reputation-derived/player anger must not leak outside village bounds,
\t\t\t\t// but never disturb an unrelated hostile-mob target.
\t\t\t\tif (this.getTarget() instanceof Player) {
\t\t\t\t\tthis.setTarget(null);
\t\t\t\t}
\t\t\t\tif (this.getLastHurtByMob() instanceof Player) {
\t\t\t\t\tthis.setLastHurtByMob(null);
\t\t\t\t}
\t\t\t}
\t\t}
\t}''',
)

# Assert the dangerous runtime reconfiguration calls are gone from the mode switch.
mode_start = text.index("\tprivate void updateConstructedNeutralTargetingMode() {")
mode_end = text.index("\n\tprivate void configureConstructedNeutralTargeting() {", mode_start)
mode_body = text[mode_start:mode_end]
if "configureConstructedVillageTargeting();" in mode_body or "configureConstructedNeutralTargeting();" in mode_body:
    raise SystemExit("Runtime target-selector reconfiguration still present in village mode switch")
if "stopBeingAngry();" in mode_body:
    raise SystemExit("Village mode switch still clears unrelated hostile-mob target state")

p.write_text(text)
print("Applied stable village-aware target selector with no runtime GoalSelector rebuilds.")
