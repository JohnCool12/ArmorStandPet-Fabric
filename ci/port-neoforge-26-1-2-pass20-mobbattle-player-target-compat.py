from pathlib import Path

root = Path('project')
golem_path = root / 'src/main/java/com/mcmoddev/golems/entity/GolemBase.java'
text = golem_path.read_text()

# Mob Battle 26.1's Utils.setTargetTo() calls Mob#setTarget(target) FIRST and only then
# flips its ActiveTargetMobbattle boolean. Therefore Extra Golems cannot require that
# flag (or any Mob Battle marker) to already be present inside setTarget(): doing so
# rejects the exact initial player assignment the Mob Enrager is trying to make.
#
# Some earlier generated V4 sources contain a reflection helper that looked for a
# nonexistent mobbattle$getForcedTargets method. Remove that dead helper when present.
helper_start = text.find('\n\t/**\n\t * Optional Mob Battle compatibility for explicit Mob Enrager / Mob Group targets.')
helper_end_marker = '\n\tprivate boolean hasVanillaVillageReputationReason'
if helper_start >= 0:
    helper_end = text.find(helper_end_marker, helper_start)
    if helper_end < 0:
        raise SystemExit('Found legacy Mob Battle helper but not its end marker')
    text = text[:helper_start] + '\n' + text[helper_end:]

method_sig = '\t@Override\n\tpublic void setTarget(@Nullable LivingEntity pTarget) {\n'
method_start = text.find(method_sig)
if method_start < 0:
    raise SystemExit('Could not locate GolemBase#setTarget')
old_target_anchor = '\t\tfinal LivingEntity oldTarget = this.getTarget();\n'
old_target_pos = text.find(old_target_anchor, method_start)
if old_target_pos < 0:
    raise SystemExit('Could not locate GolemBase#setTarget oldTarget anchor')

# Replace whatever player-veto prefix the generated source currently has (including the
# older isMobBattleForcedPlayerTarget variant) with the narrow invariant we actually need:
# explicit survival/adventure players are allowed; creative/spectator remain invalid.
new_prefix = method_sig + '''\t\t// Explicit battle-control assignments must be allowed to reach Mob#setTarget.\n\t\t// Natural Extra Golem AI still uses normal Iron Golem target-selection goals, so\n\t\t// this does not make innocent players spontaneous AI targets. Creative/spectator\n\t\t// players remain invalid even for an external direct assignment.\n\t\tif (pTarget instanceof Player player && (player.isCreative() || player.isSpectator())) {\n\t\t\treturn;\n\t\t}\n'''
text = text[:method_start] + new_prefix + text[old_target_pos:]
golem_path.write_text(text)

final = golem_path.read_text()
start = final.index('public void setTarget(@Nullable LivingEntity pTarget)')
end = final.index('\n\t@Override\n\tpublic boolean doHurtTarget', start)
block = final[start:end]

for forbidden in (
    'this.getLastHurtByMob() != player',
    '!isPersistentlyAngryAt(player, serverLevel)',
    '!hasVanillaVillageReputationReason(player, serverLevel)',
    'isMobBattleForcedPlayerTarget',
):
    if forbidden in block:
        raise SystemExit(f'Player target veto still present in setTarget: {forbidden}')

for required in (
    'pTarget instanceof Player player && (player.isCreative() || player.isSpectator())',
    'final LivingEntity oldTarget = this.getTarget();',
    'super.setTarget(pTarget);',
    'sanitizeSilentAggravationState',
    'hasVanillaVillageReputationReason',
    'recoverInterruptedDirectPlayerProvocation',
):
    if required not in final:
        raise SystemExit(f'Missing player-target compatibility invariant: {required}')

# The bogus reflection hook must not survive anywhere in the final source.
if 'mobbattle$getForcedTargets' in final or 'isMobBattleForcedPlayerTarget' in final:
    raise SystemExit('Legacy/nonexistent Mob Battle forced-target reflection still present')

print('Applied pass 20: Mob Enrager direct player targets can enter Extra Golem setTarget; natural AI and creative/spectator safeguards remain intact.')
