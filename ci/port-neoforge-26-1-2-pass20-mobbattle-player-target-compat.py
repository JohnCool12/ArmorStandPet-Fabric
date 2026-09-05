from pathlib import Path

root = Path('project')
golem_path = root / 'src/main/java/com/mcmoddev/golems/entity/GolemBase.java'
text = golem_path.read_text()

old = '''\t@Override\n\tpublic void setTarget(@Nullable LivingEntity pTarget) {\n\t\tif (pTarget instanceof Player player && this.level() instanceof ServerLevel serverLevel\n\t\t\t\t&& this.getLastHurtByMob() != player\n\t\t\t\t&& !isPersistentlyAngryAt(player, serverLevel)\n\t\t\t\t&& !hasVanillaVillageReputationReason(player, serverLevel)) {\n\t\t\treturn;\n\t\t}\n\t\tfinal LivingEntity oldTarget = this.getTarget();\n'''

new = '''\t@Override\n\tpublic void setTarget(@Nullable LivingEntity pTarget) {\n\t\t// Do not veto a valid survival/adventure player merely because vanilla Iron Golem\n\t\t// provocation/reputation state is absent. External battle-control mods (notably\n\t\t// Mob Battle's Enrager tools) intentionally call Mob#setTarget(player) before\n\t\t// installing their own forced-target state. The old guard rejected that explicit\n\t\t// request before the external controller could take effect.\n\t\t//\n\t\t// Vanilla/natural safety is still preserved by the Iron Golem target goals plus\n\t\t// sanitizeSilentAggravationState(): stale last-hurt/persistent-anger state cannot\n\t\t// resurrect an unjustified player target. Creative/spectator players remain invalid.\n\t\tif (pTarget instanceof Player player && (player.isCreative() || player.isSpectator())) {\n\t\t\treturn;\n\t\t}\n\t\tfinal LivingEntity oldTarget = this.getTarget();\n'''

if old not in text:
    raise SystemExit('Could not locate GolemBase player-target veto block')
text = text.replace(old, new, 1)
golem_path.write_text(text)

final = golem_path.read_text()
start = final.index('public void setTarget(@Nullable LivingEntity pTarget)')
end = final.index('\n\t@Override\n\tpublic boolean doHurtTarget', start)
block = final[start:end]

for forbidden in (
    'this.getLastHurtByMob() != player',
    '!isPersistentlyAngryAt(player, serverLevel)',
    '!hasVanillaVillageReputationReason(player, serverLevel)',
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

print('Applied pass 20: explicit external player targets are accepted for Extra Golems while creative/spectator and stale-anger safeguards remain intact.')
