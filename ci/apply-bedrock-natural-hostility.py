from pathlib import Path

p = Path("project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java")
text = p.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label} match, found {count}")
    text = text.replace(old, new, 1)

# One-time migration marker. Older custom builds manually forced Bedrock targets and
# persistent anger. Clearing that state exactly once prevents legacy player pursuit or
# a stale dead/remote mob target from poisoning the normal target selector after update.
replace_once(
    '\tprivate static final String NEUTRAL_CONSTRUCTED_TAG = "extra_golems_neutral_constructed";\n',
    '\tprivate static final String NEUTRAL_CONSTRUCTED_TAG = "extra_golems_neutral_constructed";\n'
    '\tprivate static final String BEDROCK_NATURAL_HOSTILITY_TAG = "extra_golems_bedrock_natural_hostility_v2";\n',
    "Bedrock migration marker constant",
)

marker = "\tprivate boolean isBedrockGolem() {\n"
helper = '''\tprivate void migrateBedrockNaturalHostilityState() {
\t\tif (!isBedrockGolem() || this.getTags().contains(BEDROCK_NATURAL_HOSTILITY_TAG)) {
\t\t\treturn;
\t\t}

\t\t// Old builds called setTarget() and, for players, synthesized persistent anger
\t\t// directly because Bedrock rejects damage. That bypassed vanilla TargetGoal
\t\t// continuation/range rules and could leave stale combat state indefinitely.
\t\t// Reset it once, then from this point on only normal target goals may select a
\t\t// target. Hostile-mob scanning resumes naturally on the following AI tick.
\t\tthis.stopBeingAngry();
\t\tthis.setLastHurtByMob(null);
\t\tthis.setTarget(null);
\t\tthis.addTag(BEDROCK_NATURAL_HOSTILITY_TAG);
\t}

'''
if text.count(marker) != 1:
    raise SystemExit(f"Expected one isBedrockGolem marker, found {text.count(marker)}")
text = text.replace(marker, helper + marker, 1)

# Run migration before the constructed-neutral/village mode maintenance so that the
# correct target selector can immediately take over from a completely clean state.
replace_once(
    "\t\tmaintainConstructedNeutralRetaliation();\n",
    "\t\tmigrateBedrockNaturalHostilityState();\n"
    "\t\tmaintainConstructedNeutralRetaliation();\n",
    "customServerAiStep maintenance hook",
)

# The strict outside-village manual player targeting remains useful for damageable
# constructed golems, but Bedrock must skip it: its attempted hit is captured below and
# HurtByTargetGoal will perform the actual target acquisition just as it does for vanilla.
replace_once(
    "\t\t\tif (isConstructedNeutral() && !isConstructedNeutralInVillage()\n"
    "\t\t\t\t\t&& sourceEntity instanceof Player player\n",
    "\t\t\tif (isConstructedNeutral() && !isConstructedNeutralInVillage()\n"
    "\t\t\t\t\t&& !isBedrockGolem()\n"
    "\t\t\t\t\t&& sourceEntity instanceof Player player\n",
    "strict outside-village Bedrock exclusion",
)

# Replace Bedrock's force-target/force-anger block with the minimum bookkeeping that a
# successful vanilla LivingEntity hit supplies to HurtByTargetGoal. This is enough to
# provoke retaliation while preserving zero damage/red flash/hurt-time, but it does not
# bypass target range, continuation, death, village reputation, or hostile-mob scanning.
old = '''\t\t\tif (isBedrockGolem() && sourceEntity instanceof LivingEntity attacker
\t\t\t\t\t&& attacker != this && attacker.isAlive()) {
\t\t\t\t// Creative/spectator players remain invalid combat targets.
\t\t\t\tif (!(attacker instanceof Player player) || (!player.isCreative() && !player.isSpectator())) {
\t\t\t\t\t// Constructed-neutral player provocation was already registered above.
\t\t\t\t\t// Other Bedrock attack attempts still need explicit bookkeeping because
\t\t\t\t\t\t// invulnerability prevents vanilla LivingEntity#hurt from doing it.
\t\t\t\t\tif (!(attacker instanceof Player) || !isConstructedNeutral()
\t\t\t\t\t\t\t|| isConstructedNeutralInVillage()) {
\t\t\t\t\t\tthis.setLastHurtByMob(attacker);
\t\t\t\t\t\tthis.setTarget(attacker);
\t\t\t\t\t}

\t\t\t\t\t// Preserve the earlier persistent Bedrock behavior only for Bedrock
\t\t\t\t\t// golems that were NOT built under the new strict-neutral construction mode.
\t\t\t\t\tif (attacker instanceof Player player
\t\t\t\t\t\t\t&& (!isConstructedNeutral() || isConstructedNeutralInVillage())) {
\t\t\t\t\t\tthis.setPersistentAngerTarget(player.getUUID());
\t\t\t\t\t\tthis.startPersistentAngerTimer();
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
'''
new = '''\t\t\tif (isBedrockGolem() && sourceEntity instanceof LivingEntity attacker
\t\t\t\t\t&& attacker != this && attacker.isAlive()) {
\t\t\t\t// Creative/spectator players remain invalid combat targets. For every
\t\t\t\t// other living attacker, record ONLY the vanilla retaliation stimulus.
\t\t\t\t// HurtByTargetGoal / DefendVillageTargetGoal / hostile-mob target goals
\t\t\t\t// decide the real target; do not force setTarget() or persistent anger.
\t\t\t\tif (!(attacker instanceof Player player) || (!player.isCreative() && !player.isSpectator())) {
\t\t\t\t\tthis.setLastHurtByMob(attacker);
\t\t\t\t}
\t\t\t}
'''
replace_once(old, new, "Bedrock forced-target hurt block")

p.write_text(text)
print("Applied vanilla-target-goal Bedrock hostility fix.")
