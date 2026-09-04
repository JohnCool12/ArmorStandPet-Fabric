from pathlib import Path

root = Path('project')
shoot_path = root / 'src/main/java/com/mcmoddev/golems/data/behavior/ShootArrowsBehavior.java'
text = shoot_path.read_text()

# Potions are lobbed, low-velocity projectiles. Unlike arrows/fire charges, do not
# allow them to fire from arbitrary distance while the golem is closing in. Match
# the witch-like behavior requested by the user: chase until actually within the
# 10-block potion range, then throw.
attack_anchor = '''\t\tif (itemstack.isEmpty()) {\n\t\t\treturn false;\n\t\t}\n\n\t\t// Do not shoot through bystanders.'''
attack_replacement = '''\t\tif (itemstack.isEmpty()) {\n\t\t\treturn false;\n\t\t}\n\n\t\t// Hard potion firing gate: splash/lingering potions are only thrown once the\n\t\t// target is truly within 10 blocks (3D distance), so they are not wasted on\n\t\t// long-range arcs that cannot reach. Other projectile types keep their existing\n\t\t// ability to fire while the golem closes distance.\n\t\tif (isThrownPotion(itemstack)\n\t\t\t\t&& mob.distanceToSqr(target) > POTION_PREFERRED_MAX_RANGE * POTION_PREFERRED_MAX_RANGE) {\n\t\t\treturn false;\n\t\t}\n\n\t\t// Do not shoot through bystanders.'''
if attack_anchor not in text:
    raise SystemExit('Could not locate ranged-attack itemstack gate for potion hard range')
text = text.replace(attack_anchor, attack_replacement, 1)

# Use the same true 3D distance for potion positioning. Normal projectiles retain the
# current horizontal preferred-range behavior, but a potion target above/below the golem
# should not cause it to stop merely because horizontal distance is <= 10 blocks.
movement_anchor = '''\t\t\tfinal double horizontalDistanceSqr = dx * dx + dz * dz;\n\t\t\tfinal boolean canSee = this.mob.getSensing().hasLineOfSight(currentTarget);\n\t\t\tfinal double preferredMaxRange = getPreferredMaximumRange(this.extraGolem);\n\n\t\t\tif (horizontalDistanceSqr > preferredMaxRange * preferredMaxRange || !canSee) {\n'''
movement_replacement = '''\t\t\tfinal double horizontalDistanceSqr = dx * dx + dz * dz;\n\t\t\tfinal boolean canSee = this.mob.getSensing().hasLineOfSight(currentTarget);\n\t\t\tfinal ItemStack nextAmmo = findFirst(this.extraGolem.getInventory(), ShootArrowsBehavior.this::isAmmo);\n\t\t\tfinal boolean potionShot = isThrownPotion(nextAmmo);\n\t\t\tfinal double preferredMaxRange = potionShot ? POTION_PREFERRED_MAX_RANGE : DEFAULT_PREFERRED_MAX_RANGE;\n\t\t\tfinal double rangeDistanceSqr = potionShot ? this.mob.distanceToSqr(currentTarget) : horizontalDistanceSqr;\n\n\t\t\tif (rangeDistanceSqr > preferredMaxRange * preferredMaxRange || !canSee) {\n'''
if movement_anchor not in text:
    raise SystemExit('Could not locate ranged positioning distance block for potion hard range')
text = text.replace(movement_anchor, movement_replacement, 1)

shoot_path.write_text(text)

final = shoot_path.read_text()
for required in (
    'mob.distanceToSqr(target) > POTION_PREFERRED_MAX_RANGE * POTION_PREFERRED_MAX_RANGE',
    'final boolean potionShot = isThrownPotion(nextAmmo);',
    'final double rangeDistanceSqr = potionShot ? this.mob.distanceToSqr(currentTarget) : horizontalDistanceSqr;',
    'if (rangeDistanceSqr > preferredMaxRange * preferredMaxRange || !canSee)',
    'POTION_PREFERRED_MAX_RANGE = 10.0D',
    'DEFAULT_PREFERRED_MAX_RANGE = 15.0D',
):
    if required not in final:
        raise SystemExit(f'Missing potion hard-range invariant: {required}')

# Ensure this change remains potion-specific and does not restore a global firing cap.
if 'if (mob.distanceToSqr(target) > DEFAULT_PREFERRED_MAX_RANGE' in final:
    raise SystemExit('Pass18 must not add a hard firing cap to non-potion projectiles')

print('Applied pass 18: Dispenser Golem only throws splash/lingering potions within a true 10-block range and chases until then.')
