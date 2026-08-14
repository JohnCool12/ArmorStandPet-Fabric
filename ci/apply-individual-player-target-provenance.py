from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s = p.read_text()

# Add a per-entity transient guard used while this golem's own vanilla
# DefendVillageTargetGoal assigns a reputation-derived player target. The fallback
# helper below independently mirrors vanilla DefendVillageTargetGoal.canUse(), so
# legitimate reputation hostility remains valid even if another Bedrock-specific
# lifecycle path reaches setTarget outside the narrow Goal.start call stack.
field_anchor = '''\t// COLOR //\n\tprivate int biomeColor = 0x83A05A;\n'''
field_repl = '''\t// COLOR //\n\tprivate int biomeColor = 0x83A05A;\n\n\t// PLAYER TARGET PROVENANCE //\n\tprivate boolean assigningVillageDefensePlayerTarget;\n'''
if s.count(field_anchor) != 1:
    raise SystemExit(f'Expected field anchor once, found {s.count(field_anchor)}')
s = s.replace(field_anchor, field_repl, 1)

old_goal = '''\t\tthis.targetSelector.addGoal(1, new DefendVillageTargetGoal(this));'''
new_goal = '''\t\tthis.targetSelector.addGoal(1, new DefendVillageTargetGoal(this) {\n\t\t\t@Override\n\t\t\tpublic void start() {\n\t\t\t\tassigningVillageDefensePlayerTarget = true;\n\t\t\t\ttry {\n\t\t\t\t\tsuper.start();\n\t\t\t\t} finally {\n\t\t\t\t\tassigningVillageDefensePlayerTarget = false;\n\t\t\t\t}\n\t\t\t}\n\t\t});'''
count = s.count(old_goal)
if count < 1:
    raise SystemExit('Natural target helper DefendVillageTargetGoal line missing')
s = s.replace(old_goal, new_goal)

set_sig = '''\t@Override\n\tpublic void setTarget(@Nullable LivingEntity pTarget) {'''
idx = s.find(set_sig)
if idx < 0:
    raise SystemExit('setTarget signature missing')
helper = '''\tprivate boolean hasVanillaVillageReputationReason(final Player player) {\n\t\tif (!(this.level() instanceof net.minecraft.server.level.ServerLevel serverLevel)\n\t\t\t\t|| player.isCreative() || player.isSpectator()) {\n\t\t\treturn false;\n\t\t}\n\t\tfinal net.minecraft.world.phys.AABB searchBox = this.getBoundingBox().inflate(10.0D, 8.0D, 10.0D);\n\t\tfinal net.minecraft.world.entity.ai.targeting.TargetingConditions targeting =\n\t\t\t\tnet.minecraft.world.entity.ai.targeting.TargetingConditions.forCombat().range(64.0D);\n\t\tif (!serverLevel.getNearbyPlayers(targeting, this, searchBox).contains(player)) {\n\t\t\treturn false;\n\t\t}\n\t\tfor (net.minecraft.world.entity.npc.Villager villager : serverLevel.getNearbyEntities(\n\t\t\t\tnet.minecraft.world.entity.npc.Villager.class, targeting, this, searchBox)) {\n\t\t\tif (villager.getPlayerReputation(player) <= -100) {\n\t\t\t\treturn true;\n\t\t\t}\n\t\t}\n\t\treturn false;\n\t}\n\n'''
s = s[:idx] + helper + s[idx:]

old_set = '''\t@Override\n\tpublic void setTarget(@Nullable LivingEntity pTarget) {\n\t\tfinal LivingEntity oldTarget = this.getTarget();\n\t\tsuper.setTarget(pTarget);\n'''
new_set = '''\t@Override\n\tpublic void setTarget(@Nullable LivingEntity pTarget) {\n\t\t// Direct retaliation must remain individual, matching vanilla Iron Golem\n\t\t// HurtByTargetGoal (which does NOT alert peers by default). A player target\n\t\t// is accepted only when THIS golem has a local reason:\n\t\t//   1) this player directly hurt this golem;\n\t\t//   2) this golem is already legitimately angry at this player; or\n\t\t//   3) this golem independently satisfies vanilla DefendVillageTargetGoal's\n\t\t//      nearby-villager reputation test for this player.\n\t\tif (pTarget instanceof Player player\n\t\t\t\t&& !assigningVillageDefensePlayerTarget\n\t\t\t\t&& this.getLastHurtByMob() != player\n\t\t\t\t&& !this.isAngryAt(player)\n\t\t\t\t&& !hasVanillaVillageReputationReason(player)) {\n\t\t\treturn;\n\t\t}\n\n\t\tfinal LivingEntity oldTarget = this.getTarget();\n\t\tsuper.setTarget(pTarget);\n'''
if s.count(old_set) != 1:
    raise SystemExit(f'Expected setTarget header once, found {s.count(old_set)}')
s = s.replace(old_set, new_set, 1)

if '.setAlertOthers(' in s:
    raise SystemExit('Unexpected executable setAlertOthers call exists in GolemBase')
for token in ('assigningVillageDefensePlayerTarget', 'hasVanillaVillageReputationReason',
              'this.getLastHurtByMob() != player', '!this.isAngryAt(player)',
              'getPlayerReputation(player) <= -100', 'inflate(10.0D, 8.0D, 10.0D)',
              'TargetingConditions.forCombat().range(64.0D)'):
    if token not in s:
        raise SystemExit(f'Missing provenance/reputation safeguard: {token}')

p.write_text(s)
print(f'Applied individual player-target provenance guard with vanilla village-reputation fallback; wrapped {count} DefendVillageTargetGoal registration(s).')
