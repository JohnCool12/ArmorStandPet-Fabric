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

# Replace the whole Bedrock special attack-attempt block by stable code boundaries,
# rather than depending on comments that changed as the hybrid village patch evolved.
start_marker = "\t\t\tif (isBedrockGolem() && sourceEntity instanceof LivingEntity attacker\n"
end_marker = "\n\n\t\t// Bedrock still exits through isInvulnerableTo() before health loss, hurtTime,\n"
start = text.find(start_marker)
if start < 0:
    raise SystemExit("Could not find Bedrock hurt block start")
end = text.find(end_marker, start)
if end < 0:
    raise SystemExit("Could not find Bedrock hurt block end")
if text.find(start_marker, start + 1) >= 0:
    raise SystemExit("Found multiple Bedrock hurt block starts")

new_block = '''\t\t\tif (isBedrockGolem() && sourceEntity instanceof LivingEntity attacker
\t\t\t\t\t&& attacker != this && attacker.isAlive()) {
\t\t\t\t// Creative/spectator players remain invalid combat targets. For every
\t\t\t\t// other living attacker, record ONLY the vanilla retaliation stimulus.
\t\t\t\t// HurtByTargetGoal / DefendVillageTargetGoal / hostile-mob target goals
\t\t\t\t// decide the real target; do not force setTarget() or persistent anger.
\t\t\t\tif (!(attacker instanceof Player player) || (!player.isCreative() && !player.isSpectator())) {
\t\t\t\t\tthis.setLastHurtByMob(attacker);
\t\t\t\t}
\t\t\t}
\t\t}'''
text = text[:start] + new_block + text[end:]

p.write_text(text)
print("Applied vanilla-target-goal Bedrock hostility fix.")
