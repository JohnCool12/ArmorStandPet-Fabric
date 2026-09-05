from pathlib import Path

root = Path('project')
shoot_path = root / 'src/main/java/com/mcmoddev/golems/data/behavior/ShootArrowsBehavior.java'
text = shoot_path.read_text()

# The inherited shooting behavior installs a +8 FOLLOW_RANGE modifier so ranged
# golems can acquire distant targets. For the Dispenser Golem this must only exist
# while it actually has a usable projectile. Empty/unshootable inventory should expose
# the underlying Iron Golem follow range unchanged rather than hard-coding a number.
text = text.replace(
    'import net.minecraft.world.entity.LivingEntity;\nimport net.minecraft.world.entity.Mob;\n',
    'import net.minecraft.world.entity.LivingEntity;\nimport net.minecraft.world.entity.Mob;\n'
    'import net.minecraft.world.entity.ai.attributes.AttributeInstance;\n'
    'import net.minecraft.world.entity.ai.attributes.Attributes;\n',
    1
)

helper_anchor = '''\tprivate boolean shouldUseMeleeNow(final IExtraGolem entity, final LivingEntity target) {\n'''
helper = '''\t/**\n\t * Keep the inherited ranged follow-range bonus strictly coupled to usable ammo.\n\t * Removing the modifier restores the entity's pre-existing/base Iron Golem-style\n\t * detection range exactly; no vanilla range value is guessed or overwritten.\n\t */\n\tprivate void syncDetectionRangeWithAmmo(final IExtraGolem entity) {\n\t\tfinal AttributeInstance followRange = entity.asMob().getAttribute(Attributes.FOLLOW_RANGE);\n\t\tif (followRange == null) {\n\t\t\treturn;\n\t\t}\n\n\t\tif (hasAmmo(entity)) {\n\t\t\tif (!followRange.hasModifier(RANGED_FOLLOW_BONUS.id())) {\n\t\t\t\tfollowRange.addTransientModifier(RANGED_FOLLOW_BONUS);\n\t\t\t}\n\t\t} else if (followRange.hasModifier(RANGED_FOLLOW_BONUS.id())) {\n\t\t\tfollowRange.removeModifier(RANGED_FOLLOW_BONUS.id());\n\t\t}\n\t}\n\n'''
if helper_anchor not in text:
    raise SystemExit('Could not locate pass16 melee-switch helper anchor')
text = text.replace(helper_anchor, helper + helper_anchor, 1)

# Normalize the modifier when goals are rebuilt. super.onRegisterGoals() adds the
# legacy permanent ranged bonus, so remove that copy and immediately re-add it as a
# transient modifier only when usable projectile ammo is currently present.
attach_anchor = '''\t@Override\n\tpublic void onAttachData(IExtraGolem entity) {\n'''
register_override = '''\t@Override\n\tpublic void onRegisterGoals(final IExtraGolem entity) {\n\t\tsuper.onRegisterGoals(entity);\n\t\tfinal AttributeInstance followRange = entity.asMob().getAttribute(Attributes.FOLLOW_RANGE);\n\t\tif (followRange != null && followRange.hasModifier(RANGED_FOLLOW_BONUS.id())) {\n\t\t\tfollowRange.removeModifier(RANGED_FOLLOW_BONUS.id());\n\t\t}\n\t\tsyncDetectionRangeWithAmmo(entity);\n\t}\n\n'''
if attach_anchor not in text:
    raise SystemExit('Could not locate ShootArrowsBehavior onAttachData anchor')
if 'public void onRegisterGoals(final IExtraGolem entity)' not in text:
    text = text.replace(attach_anchor, register_override + attach_anchor, 1)

# The dispenser's projectile inventory can change from firing, pickup, or its GUI.
# Re-evaluate every AI tick so the detection range switches effectively immediately.
tick_anchor = '''\t@Override\n\tpublic void onTick(final IExtraGolem entity) {\n\t\tsuper.onTick(entity);\n'''
tick_replacement = '''\t@Override\n\tpublic void onTick(final IExtraGolem entity) {\n\t\tsuper.onTick(entity);\n\t\tsyncDetectionRangeWithAmmo(entity);\n'''
if tick_anchor not in text:
    raise SystemExit('Could not locate pass16 ShootArrowsBehavior onTick anchor')
text = text.replace(tick_anchor, tick_replacement, 1)

shoot_path.write_text(text)

final = shoot_path.read_text()
for required in (
    'import net.minecraft.world.entity.ai.attributes.AttributeInstance;',
    'import net.minecraft.world.entity.ai.attributes.Attributes;',
    'syncDetectionRangeWithAmmo(final IExtraGolem entity)',
    'if (hasAmmo(entity))',
    'followRange.addTransientModifier(RANGED_FOLLOW_BONUS);',
    'followRange.removeModifier(RANGED_FOLLOW_BONUS.id());',
    'public void onRegisterGoals(final IExtraGolem entity)',
    'syncDetectionRangeWithAmmo(entity);',
    'public void onTick(final IExtraGolem entity)',
):
    if required not in final:
        raise SystemExit(f'Missing dynamic detection-range invariant: {required}')

# This fix must preserve the entity's existing base follow range, not replace it with
# a guessed vanilla number.
if 'setBaseValue(' in final:
    raise SystemExit('Dynamic detection patch must not overwrite FOLLOW_RANGE base value')

print('Applied pass 17: Dispenser Golem ranged detection bonus now exists only while usable projectile ammo is present.')
