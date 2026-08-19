from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s = p.read_text()

# A silent setTarget(Player) rejection can leave TargetGoal.targetMob alive. On the next
# TargetGoal.canContinueToUse(), vanilla asks mob.canAttack(target) before retrying setTarget.
# Mark only players that were ACTUALLY rejected, then make canAttack false for that stale
# player until a legitimate local hostility reason exists. This releases TARGET control
# without changing normal/direct retaliation checks for players that were never rejected.
field = '\tprivate boolean assigningVillageDefensePlayerTarget;\n'
if s.count(field) != 1:
    raise SystemExit('assigningVillageDefensePlayerTarget field missing')
s = s.replace(field, field + '\tprivate boolean evaluatingVillageReputationPlayerReason;\n\t@Nullable private java.util.UUID rejectedPlayerTarget;\n', 1)

old_helper = '''\tprivate boolean hasVanillaVillageReputationReason(final Player player) {\n\t\tif (!(this.level() instanceof net.minecraft.server.level.ServerLevel serverLevel)\n\t\t\t\t|| player.isCreative() || player.isSpectator()) {\n\t\t\treturn false;\n\t\t}\n\t\tfinal net.minecraft.world.phys.AABB searchBox = this.getBoundingBox().inflate(10.0D, 8.0D, 10.0D);\n\t\tfinal net.minecraft.world.entity.ai.targeting.TargetingConditions targeting =\n\t\t\t\tnet.minecraft.world.entity.ai.targeting.TargetingConditions.forCombat().range(64.0D);\n\t\tif (!serverLevel.getNearbyPlayers(targeting, this, searchBox).contains(player)) {\n\t\t\treturn false;\n\t\t}\n\t\tfor (net.minecraft.world.entity.npc.Villager villager : serverLevel.getNearbyEntities(\n\t\t\t\tnet.minecraft.world.entity.npc.Villager.class, targeting, this, searchBox)) {\n\t\t\tif (villager.getPlayerReputation(player) <= -100) {\n\t\t\t\treturn true;\n\t\t\t}\n\t\t}\n\t\treturn false;\n\t}\n\n'''
new_helper = '''\tprivate boolean hasVanillaVillageReputationReason(final Player player) {\n\t\tif (!(this.level() instanceof net.minecraft.server.level.ServerLevel serverLevel)\n\t\t\t\t|| player.isCreative() || player.isSpectator()) {\n\t\t\treturn false;\n\t\t}\n\t\tfinal net.minecraft.world.phys.AABB searchBox = this.getBoundingBox().inflate(10.0D, 8.0D, 10.0D);\n\t\tfinal net.minecraft.world.entity.ai.targeting.TargetingConditions targeting =\n\t\t\t\tnet.minecraft.world.entity.ai.targeting.TargetingConditions.forCombat().range(64.0D);\n\t\tevaluatingVillageReputationPlayerReason = true;\n\t\ttry {\n\t\t\tif (!serverLevel.getNearbyPlayers(targeting, this, searchBox).contains(player)) {\n\t\t\t\treturn false;\n\t\t\t}\n\t\t\tfor (net.minecraft.world.entity.npc.Villager villager : serverLevel.getNearbyEntities(\n\t\t\t\t\tnet.minecraft.world.entity.npc.Villager.class, targeting, this, searchBox)) {\n\t\t\t\tif (villager.getPlayerReputation(player) <= -100) {\n\t\t\t\t\treturn true;\n\t\t\t\t}\n\t\t\t}\n\t\t\treturn false;\n\t\t} finally {\n\t\t\tevaluatingVillageReputationPlayerReason = false;\n\t\t}\n\t}\n\n\tprivate boolean hasLocalPlayerTargetReason(final Player player) {\n\t\tif (assigningVillageDefensePlayerTarget || this.getLastHurtByMob() == player) {\n\t\t\treturn true;\n\t\t}\n\t\tfinal java.util.UUID angerTarget = this.getPersistentAngerTarget();\n\t\tif (angerTarget != null && angerTarget.equals(player.getUUID())) {\n\t\t\treturn true;\n\t\t}\n\t\tif (this.isAngryAtAllPlayers(this.level())) {\n\t\t\treturn true;\n\t\t}\n\t\treturn hasVanillaVillageReputationReason(player);\n\t}\n\n\t@Override\n\tpublic boolean canAttack(final LivingEntity target) {\n\t\tif (!super.canAttack(target)) {\n\t\t\treturn false;\n\t\t}\n\t\tif (target instanceof Player player\n\t\t\t\t&& !evaluatingVillageReputationPlayerReason\n\t\t\t\t&& rejectedPlayerTarget != null\n\t\t\t\t&& rejectedPlayerTarget.equals(player.getUUID())\n\t\t\t\t&& !hasLocalPlayerTargetReason(player)) {\n\t\t\treturn false;\n\t\t}\n\t\treturn true;\n\t}\n\n'''
if s.count(old_helper) != 1:
    raise SystemExit('village reputation helper anchor missing')
s = s.replace(old_helper, new_helper, 1)

old_guard = '''\t\tif (pTarget instanceof Player player\n\t\t\t\t&& !assigningVillageDefensePlayerTarget\n\t\t\t\t&& this.getLastHurtByMob() != player\n\t\t\t\t&& !this.isAngryAt(player)\n\t\t\t\t&& !hasVanillaVillageReputationReason(player)) {\n\t\t\treturn;\n\t\t}\n'''
new_guard = '''\t\tif (pTarget instanceof Player player) {\n\t\t\tif (!hasLocalPlayerTargetReason(player)) {\n\t\t\t\trejectedPlayerTarget = player.getUUID();\n\t\t\t\treturn;\n\t\t\t}\n\t\t\tif (rejectedPlayerTarget != null && rejectedPlayerTarget.equals(player.getUUID())) {\n\t\t\t\trejectedPlayerTarget = null;\n\t\t\t}\n\t\t}\n'''
if s.count(old_guard) != 1:
    raise SystemExit('old player setTarget provenance guard missing')
s = s.replace(old_guard, new_guard, 1)

for token in ('hasLocalPlayerTargetReason', 'public boolean canAttack(final LivingEntity target)',
              'rejectedPlayerTarget', 'evaluatingVillageReputationPlayerReason',
              'getPersistentAngerTarget()', 'this.isAngryAtAllPlayers(this.level())'):
    if token not in s:
        raise SystemExit('missing lock-fix token: ' + token)

p.write_text(s)
print('Applied narrow stale rejected-player TargetGoal unlock fix.')
