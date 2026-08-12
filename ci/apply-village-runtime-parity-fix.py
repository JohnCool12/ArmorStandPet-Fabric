from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
text = p.read_text()

# A large class of real-world saves predates our construction marker entirely.
# In the original mod, T/pumpkin-built Extra Golems were explicitly saved as
# PlayerCreated=true. Spawn-egg/command Extra Golems were not. Therefore an unmarked,
# player-created Extra Golem is the legacy signature of a manually built golem and must
# be upgraded to the natural-Iron-Golem semantics requested by the user.
needle = '''\tprivate void maintainConstructedNeutralRetaliation() {
'''
if text.count(needle) != 1:
    raise SystemExit('Missing maintenance method')
insert = '''\tprivate void migrateLegacyPlayerCreatedConstructedGolem() {
\t\tif (isBedrockGolem()) {
\t\t\treturn;
\t\t}
\t\tif (this.isPlayerCreated()
\t\t\t\t&& !this.getTags().contains(CONSTRUCTED_NATURAL_AI_TAG)
\t\t\t\t&& !isConstructedNeutral()) {
\t\t\t// Original Extra Golems used PlayerCreated=true specifically for T-built
\t\t\t// entities. Normalize that legacy state to the same natural Iron Golem
\t\t\t// targeting semantics used by newly built Extra Golems now.
\t\t\tthis.setPlayerCreated(false);
\t\t\tthis.addTag(CONSTRUCTED_NATURAL_AI_TAG);
\t\t\tthis.constructedVillageTargetingActive = false;
\t\t\tthis.stopBeingAngry();
\t\t\tthis.setLastHurtByMob(null);
\t\t\tthis.setTarget(null);
\t\t\tconfigureBedrockNaturalIronGolemTargeting();
\t\t}
\t}

'''
text = text.replace(needle, insert + needle, 1)

old = '''\t\tsuper.customServerAiStep();
\t\tmigrateBedrockNaturalHostilityState();
\t\tmaintainConstructedNeutralRetaliation();
'''
new = '''\t\tsuper.customServerAiStep();
\t\tmigrateBedrockNaturalHostilityState();
\t\tmigrateLegacyPlayerCreatedConstructedGolem();
\t\tmaintainConstructedNeutralRetaliation();
'''
if text.count(old) != 1:
    raise SystemExit('Missing customServerAiStep migration sequence')
text = text.replace(old, new, 1)

needle2 = '''\t\treadContainer(tag);
'''
if text.count(needle2) != 1:
    raise SystemExit('Expected one readContainer(tag) in load method')
load_insert = '''\t\treadContainer(tag);
\t\tif (!isBedrockGolem() && this.isPlayerCreated()
\t\t\t\t&& !this.getTags().contains(CONSTRUCTED_NATURAL_AI_TAG)
\t\t\t\t&& !isConstructedNeutral()) {
\t\t\tthis.setPlayerCreated(false);
\t\t\tthis.addTag(CONSTRUCTED_NATURAL_AI_TAG);
\t\t\tthis.constructedVillageTargetingActive = false;
\t\t\tthis.stopBeingAngry();
\t\t\tthis.setLastHurtByMob(null);
\t\t\tthis.setTarget(null);
\t\t\tconfigureBedrockNaturalIronGolemTargeting();
\t\t}
'''
text = text.replace(needle2, load_insert, 1)

if 'migrateLegacyPlayerCreatedConstructedGolem();' not in text:
    raise SystemExit('Runtime legacy migration call missing')
if 'DefendVillageTargetGoal' not in text:
    raise SystemExit('DefendVillageTargetGoal missing')

p.write_text(text)
print('Applied runtime/load migration for original PlayerCreated=true T-built Extra Golems.')
