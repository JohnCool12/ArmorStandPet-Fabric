from pathlib import Path

root = Path('project')
golem_path = root / 'src/main/java/com/mcmoddev/golems/entity/GolemBase.java'
text = golem_path.read_text()

# Mob Battle's Mob Enrager/Group system stores explicitly assigned opponents in
# ActiveTargetMobbattle#mobbattle$getForcedTargets(). GolemBase currently rejects any
# player passed to setTarget unless vanilla retaliation/anger/reputation already justifies
# that player. Because this override returns before super.setTarget(), Mob Battle's own
# Mob#setTarget mixin cannot rescue the assignment.
#
# Keep Mob Battle optional: use reflection only when a player target is being considered.
# This avoids any compile/runtime dependency when Mob Battle is absent and is deliberately
# narrower than allowing arbitrary external player target assignments.
helper_anchor = '''\tprivate boolean isPersistentlyAngryAt(final LivingEntity target, final ServerLevel serverLevel) {\n\t\treturn this.isAngryAt(target, serverLevel);\n\t}\n\n'''
helper = '''\tprivate boolean isPersistentlyAngryAt(final LivingEntity target, final ServerLevel serverLevel) {\n\t\treturn this.isAngryAt(target, serverLevel);\n\t}\n\n\t/**\n\t * Optional Mob Battle compatibility for explicit Mob Enrager / Mob Group targets.\n\t *\n\t * The Mob Battle mixin makes LivingEntity implement ActiveTargetMobbattle at runtime,\n\t * and its forced-target set is the authoritative marker that this exact opponent was\n\t * intentionally assigned by a battle tool. Reflection keeps Extra Golems independent\n\t * of Mob Battle when that mod is not installed.\n\t */\n\tprivate boolean isMobBattleForcedPlayerTarget(final Player player) {\n\t\ttry {\n\t\t\tfinal Class<?> activeTargetClass = Class.forName(\n\t\t\t\t\t\"io.github.flemmli97.mobbattle.common.utils.ActiveTargetMobbattle\",\n\t\t\t\t\tfalse, GolemBase.class.getClassLoader());\n\t\t\tif (!activeTargetClass.isInstance(this)) {\n\t\t\t\treturn false;\n\t\t\t}\n\t\t\tfinal Object forcedTargets = activeTargetClass.getMethod(\"mobbattle$getForcedTargets\").invoke(this);\n\t\t\treturn forcedTargets instanceof java.util.Set<?> set && set.contains(player.getUUID());\n\t\t} catch (ClassNotFoundException ignored) {\n\t\t\t// Mob Battle is not installed. Preserve normal Extra Golems targeting semantics.\n\t\t\treturn false;\n\t\t} catch (ReflectiveOperationException | LinkageError ignored) {\n\t\t\t// If an incompatible Mob Battle version is present, fail closed instead of\n\t\t\t// weakening the normal player-target safeguards.\n\t\t\treturn false;\n\t\t}\n\t}\n\n'''
if helper_anchor not in text:
    raise SystemExit('Could not locate GolemBase anger helper anchor')
text = text.replace(helper_anchor, helper, 1)

old_gate = '''\t@Override\n\tpublic void setTarget(@Nullable LivingEntity pTarget) {\n\t\tif (pTarget instanceof Player player && this.level() instanceof ServerLevel serverLevel\n\t\t\t\t&& this.getLastHurtByMob() != player\n\t\t\t\t&& !isPersistentlyAngryAt(player, serverLevel)\n\t\t\t\t&& !hasVanillaVillageReputationReason(player, serverLevel)) {\n\t\t\treturn;\n\t\t}\n'''
new_gate = '''\t@Override\n\tpublic void setTarget(@Nullable LivingEntity pTarget) {\n\t\tif (pTarget instanceof Player player && this.level() instanceof ServerLevel serverLevel\n\t\t\t\t&& this.getLastHurtByMob() != player\n\t\t\t\t&& !isPersistentlyAngryAt(player, serverLevel)\n\t\t\t\t&& !hasVanillaVillageReputationReason(player, serverLevel)\n\t\t\t\t&& !isMobBattleForcedPlayerTarget(player)) {\n\t\t\treturn;\n\t\t}\n'''
if old_gate not in text:
    raise SystemExit('Could not locate GolemBase player target gate')
text = text.replace(old_gate, new_gate, 1)

golem_path.write_text(text)

final = golem_path.read_text()
for required in (
    'isMobBattleForcedPlayerTarget(final Player player)',
    'io.github.flemmli97.mobbattle.common.utils.ActiveTargetMobbattle',
    'mobbattle$getForcedTargets',
    'set.contains(player.getUUID())',
    '&& !isMobBattleForcedPlayerTarget(player)',
    'catch (ClassNotFoundException ignored)',
):
    if required not in final:
        raise SystemExit(f'Missing Mob Battle forced-player compatibility invariant: {required}')

# Preserve the existing legitimate-player checks. This compatibility exception must not
# turn into a blanket permission for arbitrary player targets.
for required in (
    'this.getLastHurtByMob() != player',
    '!isPersistentlyAngryAt(player, serverLevel)',
    '!hasVanillaVillageReputationReason(player, serverLevel)',
):
    if required not in final:
        raise SystemExit(f'Existing player-target safeguard was lost: {required}')

print('Applied pass 20: Extra Golems now accept players explicitly forced by Mob Battle Mob Enrager/Group tools without weakening normal player targeting safeguards.')
