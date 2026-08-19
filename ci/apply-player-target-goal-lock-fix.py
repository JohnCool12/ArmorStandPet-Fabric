from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s = p.read_text()

# Preserve vanilla canAttack completely. The deadlock occurs because TargetGoal can fall
# back to its protected targetMob after the golem's current target is cleared. If that
# stored target is the old player, GolemBase.setTarget(player) may correctly reject it,
# but vanilla TargetGoal.canContinueToUse() has already decided to remain active.
# Fix that specifically for HurtByTargetGoal: before vanilla continuation, reject a stale
# fallback player if this golem no longer has a local hostility reason for that player.

old_helper = '''\tprivate boolean hasVanillaVillageReputationReason(final Player player) {\n\t\tif (!(this.level() instanceof net.minecraft.server.level.ServerLevel serverLevel)\n\t\t\t\t|| player.isCreative() || player.isSpectator()) {\n\t\t\treturn false;\n\t\t}\n\t\tfinal net.minecraft.world.phys.AABB searchBox = this.getBoundingBox().inflate(10.0D, 8.0D, 10.0D);\n\t\tfinal net.minecraft.world.entity.ai.targeting.TargetingConditions targeting =\n\t\t\t\tnet.minecraft.world.entity.ai.targeting.TargetingConditions.forCombat().range(64.0D);\n\t\tif (!serverLevel.getNearbyPlayers(targeting, this, searchBox).contains(player)) {\n\t\t\treturn false;\n\t\t}\n\t\tfor (net.minecraft.world.entity.npc.Villager villager : serverLevel.getNearbyEntities(\n\t\t\t\tnet.minecraft.world.entity.npc.Villager.class, targeting, this, searchBox)) {\n\t\t\tif (villager.getPlayerReputation(player) <= -100) {\n\t\t\t\treturn true;\n\t\t\t}\n\t\t}\n\t\treturn false;\n\t}\n\n'''
new_helper = old_helper + '''\tprivate boolean hasLocalPlayerTargetReason(final Player player) {\n\t\treturn assigningVillageDefensePlayerTarget\n\t\t\t\t|| this.getLastHurtByMob() == player\n\t\t\t\t|| this.isAngryAt(player)\n\t\t\t\t|| hasVanillaVillageReputationReason(player);\n\t}\n\n'''
if s.count(old_helper) != 1:
    raise SystemExit('village reputation helper anchor missing')
s = s.replace(old_helper, new_helper, 1)

old_guard = '''\t\tif (pTarget instanceof Player player\n\t\t\t\t&& !assigningVillageDefensePlayerTarget\n\t\t\t\t&& this.getLastHurtByMob() != player\n\t\t\t\t&& !this.isAngryAt(player)\n\t\t\t\t&& !hasVanillaVillageReputationReason(player)) {\n\t\t\treturn;\n\t\t}\n'''
new_guard = '''\t\tif (pTarget instanceof Player player\n\t\t\t\t&& !hasLocalPlayerTargetReason(player)) {\n\t\t\treturn;\n\t\t}\n'''
if s.count(old_guard) != 1:
    raise SystemExit('old player setTarget provenance guard missing')
s = s.replace(old_guard, new_guard, 1)

needle = 'new HurtByTargetGoal(this)'
count = s.count(needle)
if count < 1:
    raise SystemExit('No HurtByTargetGoal(this) constructors found')
replacement = '''new HurtByTargetGoal(this) {\n\t\t\t@Override\n\t\t\tpublic boolean canContinueToUse() {\n\t\t\t\tLivingEntity candidate = GolemBase.this.getTarget();\n\t\t\t\tif (candidate == null) {\n\t\t\t\t\tcandidate = this.targetMob;\n\t\t\t\t}\n\t\t\t\tif (candidate instanceof Player player\n\t\t\t\t\t\t&& !GolemBase.this.hasLocalPlayerTargetReason(player)) {\n\t\t\t\t\treturn false;\n\t\t\t\t}\n\t\t\t\treturn super.canContinueToUse();\n\t\t\t}\n\t\t}'''
s = s.replace(needle, replacement)

if 'public boolean canAttack(final LivingEntity target)' in s or 'rejectedPlayerTarget' in s:
    raise SystemExit('Broad canAttack/rejected-player implementation unexpectedly present')
if s.count('hasLocalPlayerTargetReason') < 3:
    raise SystemExit('Local player hostility helper not wired into setter and HurtBy continuation')

p.write_text(s)
print(f'Applied HurtByTargetGoal stale-player continuation fix to {count} target-stack occurrence(s).')
