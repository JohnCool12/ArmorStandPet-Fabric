from pathlib import Path

root = Path('project')
shoot_path = root / 'src/main/java/com/mcmoddev/golems/data/behavior/ShootArrowsBehavior.java'
data_path = root / 'src/main/java/com/mcmoddev/golems/data/behavior/data/ShootBehaviorData.java'

text = shoot_path.read_text()

# Goal + EnumSet are used by the custom ranged-position controller.
text = text.replace(
    'import net.minecraft.world.entity.ai.goal.MeleeAttackGoal;\nimport net.minecraft.world.entity.ai.goal.RangedAttackGoal;',
    'import net.minecraft.world.entity.ai.goal.Goal;\nimport net.minecraft.world.entity.ai.goal.MeleeAttackGoal;\nimport net.minecraft.world.entity.ai.goal.RangedAttackGoal;'
)
text = text.replace(
    'import java.util.List;\nimport java.util.Objects;',
    'import java.util.EnumSet;\nimport java.util.List;\nimport java.util.Objects;'
)

old_constants = '''\t// Warden-inspired switch condition: if the golem has failed to LAND a melee\n\t// hit on the same target for ten seconds, ranged fire becomes available.\n\tprivate static final long MELEE_FAILURE_FALLBACK_TICKS = 10L * 20L;\n\tprivate static final double WARDEN_HORIZONTAL_RANGE_SQR = 15.0D * 15.0D;\n\tprivate static final double WARDEN_VERTICAL_RANGE = 20.0D;\n\tprivate static final double RANGED_DISTANCE_FACTOR_RANGE = 32.0D;\n'''
new_constants = '''\t// Preserve the requested ten-second initial ranged warmup, then use the\n\t// Dispenser Golem's original data-driven firing cadence. Movement is handled\n\t// independently as a ranged pursuit instead of melee pursuit.\n\tprivate static final long RANGED_WARMUP_TICKS = 10L * 20L;\n\tprivate static final double WARDEN_HORIZONTAL_RANGE_SQR = 15.0D * 15.0D;\n\tprivate static final double WARDEN_VERTICAL_RANGE = 20.0D;\n\tprivate static final double RANGED_DISTANCE_FACTOR_RANGE = 32.0D;\n\n\t// Fluid ranged-positioning band. Stay close enough for reliable projectiles,\n\t// chase immediately if the target stretches the gap, and retreat if crowded.\n\tprivate static final double PREFERRED_MIN_RANGE = 8.0D;\n\tprivate static final double PREFERRED_MAX_RANGE = 12.0D;\n\tprivate static final double PREFERRED_MIN_RANGE_SQR = PREFERRED_MIN_RANGE * PREFERRED_MIN_RANGE;\n\tprivate static final double PREFERRED_MAX_RANGE_SQR = PREFERRED_MAX_RANGE * PREFERRED_MAX_RANGE;\n\tprivate static final double CHASE_SPEED = 1.08D;\n\tprivate static final double RETREAT_SPEED = 1.02D;\n\tprivate static final float COMBAT_STRAFE_SPEED = 0.32F;\n'''
if old_constants not in text:
    raise SystemExit('Could not locate v2 ranged constants')
text = text.replace(old_constants, new_constants, 1)

old_attach = '''\t@Override\n\tpublic void onAttachData(IExtraGolem entity) {\n\t\t// The melee goal owns movement at all times, so the golem keeps closing distance\n\t\t// while a ranged shot is layered on top of the chase.\n\t\tfinal RangedAttackGoal rangedGoal = new RangedAttackGoal(entity.asMob(), 1.0D, getAttackInterval(), 32.0F);\n\t\tfinal MeleeAttackGoal meleeGoal = new MeleeAttackGoal(entity.asMob(), 1.0D, true);\n\t\tentity.attachBehaviorData(new ShootBehaviorData(entity, rangedGoal, meleeGoal));\n\t}\n\n\t@Override\n\tprotected void updateCombatTask(final IExtraGolem entity, final boolean forceMelee) {\n\t\tfinal Mob mob = entity.asMob();\n\t\tgetShootData(entity).ifPresent(data -> {\n\t\t\tmob.goalSelector.removeGoal(data.getRangedGoal());\n\t\t\tmob.goalSelector.removeGoal(data.getMeleeGoal());\n\t\t\tmob.goalSelector.addGoal(0, data.getMeleeGoal());\n\t\t});\n\t}\n'''
new_attach = '''\t@Override\n\tpublic void onAttachData(IExtraGolem entity) {\n\t\t// Keep the legacy goal objects only because ShootBehaviorData/other shoot\n\t\t// infrastructure expects them. Neither owns movement for the dispenser now.\n\t\tfinal RangedAttackGoal rangedGoal = new RangedAttackGoal(entity.asMob(), 1.0D, getAttackInterval(), 32.0F);\n\t\tfinal MeleeAttackGoal meleeGoal = new MeleeAttackGoal(entity.asMob(), 1.0D, true);\n\t\tentity.attachBehaviorData(new ShootBehaviorData(entity, rangedGoal, meleeGoal));\n\n\t\t// Priority 0 and MOVE/LOOK flags pre-empt vanilla IronGolem melee movement while\n\t\t// ammunition exists, without replacing target selection or other V4 behavior.\n\t\tentity.asMob().goalSelector.addGoal(0, new FluidRangedPositionGoal(entity));\n\t}\n\n\t@Override\n\tprotected void updateCombatTask(final IExtraGolem entity, final boolean forceMelee) {\n\t\t// Never switch this behavior back to vanilla RangedAttackGoal (which freezes\n\t\t// once in range) or the dedicated melee goal. FluidRangedPositionGoal controls\n\t\t// movement while ammo exists; vanilla golem AI can still act if ammo is empty.\n\t\tfinal Mob mob = entity.asMob();\n\t\tgetShootData(entity).ifPresent(data -> {\n\t\t\tmob.goalSelector.removeGoal(data.getRangedGoal());\n\t\t\tmob.goalSelector.removeGoal(data.getMeleeGoal());\n\t\t});\n\t}\n'''
if old_attach not in text:
    raise SystemExit('Could not locate v2 onAttach/updateCombatTask block')
text = text.replace(old_attach, new_attach, 1)

old_attack_hook = '''\t@Override\n\tpublic void onAttack(final IExtraGolem entity, final net.minecraft.world.entity.Entity target) {\n\t\t// Only an ACTUAL landed melee attack resets the ten-second fallback timer.\n\t\t// Being geometrically close enough to swing is deliberately not sufficient.\n\t\tfinal long gameTime = entity.asMob().level().getGameTime();\n\t\tgetShootData(entity).ifPresent(data -> data.markSuccessfulMeleeHit(gameTime));\n\t}\n'''
new_attack_hook = '''\t@Override\n\tpublic void onAttack(final IExtraGolem entity, final net.minecraft.world.entity.Entity target) {\n\t\t// Ranged positioning deliberately does not depend on melee contact anymore.\n\t\t// Leave this hook empty so incidental contact cannot reset the ranged warmup.\n\t}\n'''
if old_attack_hook not in text:
    raise SystemExit('Could not locate v2 onAttack hook')
text = text.replace(old_attack_hook, new_attack_hook, 1)

old_warmup = '''\t\t\t// The key distinction is successful contact, not nominal melee range. If a\n\t\t\t// target is standing 2 blocks away but is elevated, obstructed, or otherwise\n\t\t\t// impossible to hit, ten seconds without a landed melee hit still unlocks fire.\n\t\t\tif (!data.hasGoneWithoutSuccessfulMeleeHitFor(gameTime, MELEE_FAILURE_FALLBACK_TICKS)) {\n\t\t\t\treturn;\n\t\t\t}\n'''
new_warmup = '''\t\t\t// The first ranged shot unlocks after ten seconds tracking this target.\n\t\t\t// Movement is ranged from the start, so there is no forced melee approach.\n\t\t\tif (!data.hasTrackedTargetFor(gameTime, RANGED_WARMUP_TICKS)) {\n\t\t\t\treturn;\n\t\t\t}\n'''
if old_warmup not in text:
    raise SystemExit('Could not locate v2 melee-failure warmup block')
text = text.replace(old_warmup, new_warmup, 1)

anchor = '''\n\t@Override\n\tpublic List<Component> createDescriptions(RegistryAccess registryAccess) {\n'''
movement_goal = '''\n\t/**\n\t * Ranged movement that stays responsive while the independent shooting timer runs.\n\t * It chases a fleeing target, retreats from pressure, and strafes in the useful\n\t * firing band instead of standing still or walking all the way into melee range.\n\t */\n\tprivate final class FluidRangedPositionGoal extends Goal {\n\t\tprivate final IExtraGolem extraGolem;\n\t\tprivate final Mob mob;\n\t\tprivate LivingEntity target;\n\t\tprivate int strafeDirection = 1;\n\t\tprivate int strafeTime;\n\n\t\tprivate FluidRangedPositionGoal(final IExtraGolem extraGolem) {\n\t\t\tthis.extraGolem = extraGolem;\n\t\t\tthis.mob = extraGolem.asMob();\n\t\t\tthis.setFlags(EnumSet.of(Flag.MOVE, Flag.LOOK));\n\t\t}\n\n\t\t@Override\n\t\tpublic boolean canUse() {\n\t\t\tthis.target = this.mob.getTarget();\n\t\t\treturn this.target != null && this.target.isAlive() && hasAmmo(this.extraGolem);\n\t\t}\n\n\t\t@Override\n\t\tpublic boolean canContinueToUse() {\n\t\t\tthis.target = this.mob.getTarget();\n\t\t\treturn this.target != null && this.target.isAlive() && hasAmmo(this.extraGolem);\n\t\t}\n\n\t\t@Override\n\t\tpublic void stop() {\n\t\t\tthis.target = null;\n\t\t\tthis.mob.getNavigation().stop();\n\t\t}\n\n\t\t@Override\n\t\tpublic void tick() {\n\t\t\tfinal LivingEntity currentTarget = this.target;\n\t\t\tif (currentTarget == null) {\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\tthis.mob.getLookControl().setLookAt(currentTarget, 30.0F, 30.0F);\n\t\t\tfinal double dx = currentTarget.getX() - this.mob.getX();\n\t\t\tfinal double dz = currentTarget.getZ() - this.mob.getZ();\n\t\t\tfinal double horizontalDistanceSqr = dx * dx + dz * dz;\n\t\t\tfinal boolean canSee = this.mob.getSensing().hasLineOfSight(currentTarget);\n\n\t\t\tif (horizontalDistanceSqr < PREFERRED_MIN_RANGE_SQR) {\n\t\t\t\t// Back away along the target->golem vector. Navigation gives this obstacle\n\t\t\t\t// awareness rather than blindly applying reverse velocity into a wall.\n\t\t\t\tdouble awayX = this.mob.getX() - currentTarget.getX();\n\t\t\t\tdouble awayZ = this.mob.getZ() - currentTarget.getZ();\n\t\t\t\tfinal double length = Math.sqrt(awayX * awayX + awayZ * awayZ);\n\t\t\t\tif (length > 1.0E-4D) {\n\t\t\t\t\tawayX /= length;\n\t\t\t\t\tawayZ /= length;\n\t\t\t\t\tfinal double retreat = PREFERRED_MIN_RANGE - Math.sqrt(horizontalDistanceSqr) + 2.0D;\n\t\t\t\t\tthis.mob.getNavigation().moveTo(\n\t\t\t\t\t\t\tthis.mob.getX() + awayX * retreat,\n\t\t\t\t\t\t\tthis.mob.getY(),\n\t\t\t\t\t\t\tthis.mob.getZ() + awayZ * retreat,\n\t\t\t\t\t\t\tRETREAT_SPEED);\n\t\t\t\t} else {\n\t\t\t\t\tthis.mob.getNavigation().stop();\n\t\t\t\t}\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\tif (horizontalDistanceSqr > PREFERRED_MAX_RANGE_SQR || !canSee) {\n\t\t\t\t// The target is escaping (or cover broke the shot): immediately pursue,\n\t\t\t\t// but the close-range branch above prevents pursuit from collapsing to melee.\n\t\t\t\tthis.mob.getNavigation().moveTo(currentTarget, CHASE_SPEED);\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\t// Useful firing band: do not freeze like vanilla RangedAttackGoal. A gentle\n\t\t\t// alternating strafe keeps the golem visually fluid without ruining accuracy.\n\t\t\tthis.mob.getNavigation().stop();\n\t\t\tif (++this.strafeTime >= 50) {\n\t\t\t\tthis.strafeTime = 0;\n\t\t\t\tthis.strafeDirection = -this.strafeDirection;\n\t\t\t}\n\t\t\tthis.mob.getMoveControl().strafe(0.05F, COMBAT_STRAFE_SPEED * this.strafeDirection);\n\t\t}\n\t}\n'''
if anchor not in text:
    raise SystemExit('Could not locate descriptions anchor for movement goal')
text = text.replace(anchor, movement_goal + anchor, 1)
shoot_path.write_text(text)

data = data_path.read_text()
data_anchor = '''\tpublic void markSuccessfulMeleeHit(final long gameTime) {\n'''
data_insert = '''\tpublic boolean hasTrackedTargetFor(final long gameTime, final long ticks) {\n\t\treturn this.trackedTarget != null\n\t\t\t\t&& this.targetAcquiredGameTime != Long.MIN_VALUE\n\t\t\t\t&& gameTime - this.targetAcquiredGameTime >= ticks;\n\t}\n\n'''
if data_anchor not in data:
    raise SystemExit('Could not locate ShootBehaviorData timer insertion anchor')
if 'public boolean hasTrackedTargetFor(' not in data:
    data = data.replace(data_anchor, data_insert + data_anchor, 1)
data_path.write_text(data)

final = shoot_path.read_text()
for required in (
    'new FluidRangedPositionGoal(entity)',
    'PREFERRED_MIN_RANGE = 8.0D',
    'PREFERRED_MAX_RANGE = 12.0D',
    'this.mob.getNavigation().moveTo(currentTarget, CHASE_SPEED);',
    'this.mob.getMoveControl().strafe(0.05F, COMBAT_STRAFE_SPEED * this.strafeDirection);',
    'data.hasTrackedTargetFor(gameTime, RANGED_WARMUP_TICKS)',
    'data.hasRangedShotCooldownElapsed(gameTime, getAttackInterval())',
    'itemstack.is(Items.FIRE_CHARGE)',
):
    if required not in final:
        raise SystemExit(f'Missing ranged-position invariant: {required}')

print('Applied pass 14: fluid ranged pursuit/spacing for Dispenser Golem; no forced melee approach.')
