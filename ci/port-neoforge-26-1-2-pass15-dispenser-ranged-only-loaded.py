from pathlib import Path

root = Path('project')
shoot_path = root / 'src/main/java/com/mcmoddev/golems/data/behavior/ShootArrowsBehavior.java'
text = shoot_path.read_text()

# Potion projectile types used for real splash/lingering potion throws.
text = text.replace(
    'import net.minecraft.world.entity.projectile.hurtingprojectile.SmallFireball;\n',
    'import net.minecraft.world.entity.projectile.hurtingprojectile.SmallFireball;\n'
    'import net.minecraft.world.entity.projectile.throwableitemprojectile.ThrownLingeringPotion;\n'
    'import net.minecraft.world.entity.projectile.throwableitemprojectile.ThrownSplashPotion;\n'
)

old_constants = '''\t// Preserve the requested ten-second initial ranged warmup, then use the\n\t// Dispenser Golem's original data-driven firing cadence. Movement is handled\n\t// independently as a ranged pursuit instead of melee pursuit.\n\tprivate static final long RANGED_WARMUP_TICKS = 10L * 20L;\n\tprivate static final double WARDEN_HORIZONTAL_RANGE_SQR = 15.0D * 15.0D;\n\tprivate static final double WARDEN_VERTICAL_RANGE = 20.0D;\n\tprivate static final double RANGED_DISTANCE_FACTOR_RANGE = 32.0D;\n\n\t// Fluid ranged-positioning band. Stay close enough for reliable projectiles,\n\t// chase immediately if the target stretches the gap, and retreat if crowded.\n\tprivate static final double PREFERRED_MIN_RANGE = 8.0D;\n\tprivate static final double PREFERRED_MAX_RANGE = 12.0D;\n\tprivate static final double PREFERRED_MIN_RANGE_SQR = PREFERRED_MIN_RANGE * PREFERRED_MIN_RANGE;\n\tprivate static final double PREFERRED_MAX_RANGE_SQR = PREFERRED_MAX_RANGE * PREFERRED_MAX_RANGE;\n\tprivate static final double CHASE_SPEED = 1.08D;\n\tprivate static final double RETREAT_SPEED = 1.02D;\n\tprivate static final float COMBAT_STRAFE_SPEED = 0.32F;\n'''
new_constants = '''\t// With anything loaded in the dispenser compartment, this golem is ranged-only.\n\t// It has no minimum spacing: it only closes distance when the target is beyond\n\t// the preferred maximum. Normal projectiles prefer 15 blocks; thrown potions\n\t// prefer 10 so their splash/lingering impact remains useful.\n\tprivate static final double DEFAULT_PREFERRED_MAX_RANGE = 15.0D;\n\tprivate static final double POTION_PREFERRED_MAX_RANGE = 10.0D;\n\tprivate static final double CHASE_SPEED = 1.08D;\n\tprivate static final double RANGED_DISTANCE_FACTOR_RANGE = 32.0D;\n'''
if old_constants not in text:
    raise SystemExit('Could not locate pass14 ranged constants')
text = text.replace(old_constants, new_constants, 1)

old_branch = '''\t\tif (itemstack.getItem() instanceof ArrowItem) {\n\t\t\tfired = shootArrow(entity, target, itemstack, distanceFactor, start);\n\t\t} else if (itemstack.is(Items.FIRE_CHARGE)) {\n\t\t\tfired = shootFireCharge(entity, target, start);\n\t\t} else if (itemstack.getItem() instanceof ProjectileItem projectileItem && !itemstack.is(Items.ENDER_PEARL)) {\n\t\t\tfired = shootProjectileItem(entity, target, itemstack, projectileItem, start);\n\t\t} else {\n'''
new_branch = '''\t\tif (itemstack.getItem() instanceof ArrowItem) {\n\t\t\tfired = shootArrow(entity, target, itemstack, distanceFactor, start);\n\t\t} else if (itemstack.is(Items.FIRE_CHARGE)) {\n\t\t\tfired = shootFireCharge(entity, target, start);\n\t\t} else if (isThrownPotion(itemstack)) {\n\t\t\tfired = shootThrownPotion(entity, target, itemstack, start);\n\t\t} else if (itemstack.getItem() instanceof ProjectileItem projectileItem && !itemstack.is(Items.ENDER_PEARL)) {\n\t\t\tfired = shootProjectileItem(entity, target, itemstack, projectileItem, start);\n\t\t} else {\n'''
if old_branch not in text:
    raise SystemExit('Could not locate projectile selection branch')
text = text.replace(old_branch, new_branch, 1)

fire_charge_end = '''\t\tmob.playSound(SoundEvents.FIRECHARGE_USE, 1.0F, 0.8F + mob.getRandom().nextFloat() * 0.4F);\n\t\treturn true;\n\t}\n\n\tprivate boolean shootProjectileItem'''
potion_method = '''\t\tmob.playSound(SoundEvents.FIRECHARGE_USE, 1.0F, 0.8F + mob.getRandom().nextFloat() * 0.4F);\n\t\treturn true;\n\t}\n\n\tprivate boolean shootThrownPotion(final IExtraGolem entity, final LivingEntity target, final ItemStack itemstack, final Vec3 start) {\n\t\tfinal Mob mob = entity.asMob();\n\t\tfinal Projectile potion = itemstack.is(Items.LINGERING_POTION)\n\t\t\t\t? new ThrownLingeringPotion(mob.level(), mob, itemstack.copyWithCount(1))\n\t\t\t\t: new ThrownSplashPotion(mob.level(), mob, itemstack.copyWithCount(1));\n\t\tpotion.setPos(start.x, start.y, start.z);\n\t\tfinal double dx = target.getX() - start.x;\n\t\tfinal double dy = target.getY(0.5D) - start.y;\n\t\tfinal double dz = target.getZ() - start.z;\n\t\tfinal double horizontal = Math.sqrt(dx * dx + dz * dz);\n\t\t// Match the familiar lobbed potion trajectory: lower speed than arrows and\n\t\t// a modest upward lead so shots around the preferred 10-block range land well.\n\t\tpotion.shoot(dx, dy + horizontal * 0.2D, dz, 0.75F, 8.0F);\n\t\tmob.level().addFreshEntity(potion);\n\t\tmob.playSound(SoundEvents.ARROW_SHOOT, 1.0F, 0.9F + mob.getRandom().nextFloat() * 0.2F);\n\t\treturn true;\n\t}\n\n\tprivate boolean shootProjectileItem'''
if fire_charge_end not in text:
    raise SystemExit('Could not locate fire-charge method end')
text = text.replace(fire_charge_end, potion_method, 1)

old_ammo = '''\t@Override\n\tpublic boolean isAmmo(ItemStack itemStack) {\n\t\tif (!consume()) {\n\t\t\treturn false;\n\t\t}\n\t\tif (itemStack.getItem() instanceof ArrowItem || itemStack.is(Items.FIRE_CHARGE)) {\n\t\t\treturn true;\n\t\t}\n\t\t// Accept Minecraft's dispenser/entity projectile items broadly, but exclude\n\t\t// ender pearls because their owner-teleport semantics would teleport the golem.\n\t\treturn itemStack.getItem() instanceof ProjectileItem && !itemStack.is(Items.ENDER_PEARL);\n\t}\n'''
new_ammo = '''\tprivate static boolean isThrownPotion(final ItemStack itemStack) {\n\t\treturn itemStack.is(Items.SPLASH_POTION) || itemStack.is(Items.LINGERING_POTION);\n\t}\n\n\t@Override\n\tpublic boolean isAmmo(ItemStack itemStack) {\n\t\tif (!consume()) {\n\t\t\treturn false;\n\t\t}\n\t\tif (itemStack.getItem() instanceof ArrowItem || itemStack.is(Items.FIRE_CHARGE) || isThrownPotion(itemStack)) {\n\t\t\treturn true;\n\t\t}\n\t\t// Accept Minecraft's dispenser/entity projectile items broadly, but exclude\n\t\t// ender pearls because their owner-teleport semantics would teleport the golem.\n\t\treturn itemStack.getItem() instanceof ProjectileItem && !itemStack.is(Items.ENDER_PEARL);\n\t}\n'''
if old_ammo not in text:
    raise SystemExit('Could not locate ammo predicate block')
text = text.replace(old_ammo, new_ammo, 1)

old_attach_comment = '''\t\t// Priority 0 and MOVE/LOOK flags pre-empt vanilla IronGolem melee movement while\n\t\t// ammunition exists, without replacing target selection or other V4 behavior.\n\t\tentity.asMob().goalSelector.addGoal(0, new FluidRangedPositionGoal(entity));\n'''
new_attach_comment = '''\t\t// Priority 0 and MOVE/LOOK flags suppress vanilla Iron Golem melee movement\n\t\t// whenever ANY item occupies the compartment. Empty compartment = normal melee.\n\t\tentity.asMob().goalSelector.addGoal(0, new FluidRangedPositionGoal(entity));\n'''
if old_attach_comment not in text:
    raise SystemExit('Could not locate ranged-goal attach comment')
text = text.replace(old_attach_comment, new_attach_comment, 1)

old_update_comment = '''\t\t// Never switch this behavior back to vanilla RangedAttackGoal (which freezes\n\t\t// once in range) or the dedicated melee goal. FluidRangedPositionGoal controls\n\t\t// movement while ammo exists; vanilla golem AI can still act if ammo is empty.\n'''
new_update_comment = '''\t\t// Never install the legacy ranged/melee goals here. The priority-0 ranged\n\t\t// position goal blocks normal melee whenever the compartment is non-empty;\n\t\t// when the compartment is empty it stops, exposing normal Iron Golem melee AI.\n'''
if old_update_comment not in text:
    raise SystemExit('Could not locate updateCombatTask comment')
text = text.replace(old_update_comment, new_update_comment, 1)

old_attack_hook = '''\t@Override\n\tpublic void onAttack(final IExtraGolem entity, final net.minecraft.world.entity.Entity target) {\n\t\t// Ranged positioning deliberately does not depend on melee contact anymore.\n\t\t// Leave this hook empty so incidental contact cannot reset the ranged warmup.\n\t}\n'''
new_attack_hook = '''\t@Override\n\tpublic void onAttack(final IExtraGolem entity, final net.minecraft.world.entity.Entity target) {\n\t\t// Loaded ranged mode owns MOVE/LOOK at higher priority, so normal melee cannot\n\t\t// run. This hook intentionally does not influence ranged timing.\n\t}\n'''
if old_attack_hook not in text:
    raise SystemExit('Could not locate pass14 onAttack hook')
text = text.replace(old_attack_hook, new_attack_hook, 1)

old_tick_gate = '''\t\tgetShootData(entity).ifPresent(data -> {\n\t\t\tdata.trackTarget(target, gameTime);\n\t\t\tif (target == null || !target.isAlive() || !hasAmmo(entity)) {\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\tfinal double dx = target.getX() - mob.getX();\n\t\t\tfinal double dz = target.getZ() - mob.getZ();\n\t\t\tfinal double dy = Math.abs(target.getY() - mob.getY());\n\t\t\tif (dx * dx + dz * dz > WARDEN_HORIZONTAL_RANGE_SQR || dy > WARDEN_VERTICAL_RANGE) {\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\t// The first ranged shot unlocks after ten seconds tracking this target.\n\t\t\t// Movement is ranged from the start, so there is no forced melee approach.\n\t\t\tif (!data.hasTrackedTargetFor(gameTime, RANGED_WARMUP_TICKS)) {\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\t// Once fallback is active, restore the Dispenser Golem's original data-driven\n\t\t\t// ranged cadence (28 ticks / 1.4 s in dispenser.json), rather than imposing\n\t\t\t// the Warden's two-second post-attack cooldown.\n'''
new_tick_gate = '''\t\tgetShootData(entity).ifPresent(data -> {\n\t\t\tdata.trackTarget(target, gameTime);\n\t\t\tif (target == null || !target.isAlive() || !hasAmmo(entity)) {\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\t// No warmup and no maximum firing-distance gate. The target system itself\n\t\t\t// decides whether the golem is still provoked; while it is, ranged fire can\n\t\t\t// continue even beyond 16 blocks as navigation closes the gap.\n\t\t\t// Preserve the Dispenser Golem's original 28-tick data-driven firing cadence.\n'''
if old_tick_gate not in text:
    raise SystemExit('Could not locate pass14 tick gating block')
text = text.replace(old_tick_gate, new_tick_gate, 1)

start_marker = '''\t/**\n\t * Ranged movement that stays responsive while the independent shooting timer runs.\n'''
end_marker = '''\n\t@Override\n\tpublic List<Component> createDescriptions(RegistryAccess registryAccess) {\n'''
start_i = text.find(start_marker)
end_i = text.find(end_marker, start_i)
if start_i < 0 or end_i < 0:
    raise SystemExit('Could not locate FluidRangedPositionGoal block')
new_goal = '''\tprivate boolean hasCompartmentContents(final IExtraGolem entity) {\n\t\tif (!consume()) {\n\t\t\treturn true;\n\t\t}\n\t\tfinal var inventory = entity.getInventory();\n\t\tfor (int i = 0; i < inventory.getContainerSize(); i++) {\n\t\t\tif (!inventory.getItem(i).isEmpty()) {\n\t\t\t\treturn true;\n\t\t\t}\n\t\t}\n\t\treturn false;\n\t}\n\n\tprivate double getPreferredMaximumRange(final IExtraGolem entity) {\n\t\tif (!consume()) {\n\t\t\treturn DEFAULT_PREFERRED_MAX_RANGE;\n\t\t}\n\t\tfinal ItemStack nextAmmo = findFirst(entity.getInventory(), this::isAmmo);\n\t\treturn isThrownPotion(nextAmmo) ? POTION_PREFERRED_MAX_RANGE : DEFAULT_PREFERRED_MAX_RANGE;\n\t}\n\n\t/**\n\t * Ranged-only positioning while the compartment contains anything. There is no\n\t * minimum distance and no strafing/retreat behavior: stay put at or inside the\n\t * projectile's preferred maximum range, otherwise chase inward while shooting.\n\t */\n\tprivate final class FluidRangedPositionGoal extends Goal {\n\t\tprivate final IExtraGolem extraGolem;\n\t\tprivate final Mob mob;\n\t\tprivate LivingEntity target;\n\n\t\tprivate FluidRangedPositionGoal(final IExtraGolem extraGolem) {\n\t\t\tthis.extraGolem = extraGolem;\n\t\t\tthis.mob = extraGolem.asMob();\n\t\t\tthis.setFlags(EnumSet.of(Flag.MOVE, Flag.LOOK));\n\t\t}\n\n\t\t@Override\n\t\tpublic boolean canUse() {\n\t\t\tthis.target = this.mob.getTarget();\n\t\t\treturn this.target != null && this.target.isAlive() && hasCompartmentContents(this.extraGolem);\n\t\t}\n\n\t\t@Override\n\t\tpublic boolean canContinueToUse() {\n\t\t\tthis.target = this.mob.getTarget();\n\t\t\treturn this.target != null && this.target.isAlive() && hasCompartmentContents(this.extraGolem);\n\t\t}\n\n\t\t@Override\n\t\tpublic void stop() {\n\t\t\tthis.target = null;\n\t\t\tthis.mob.getNavigation().stop();\n\t\t}\n\n\t\t@Override\n\t\tpublic void tick() {\n\t\t\tfinal LivingEntity currentTarget = this.target;\n\t\t\tif (currentTarget == null) {\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\tthis.mob.getLookControl().setLookAt(currentTarget, 30.0F, 30.0F);\n\t\t\tfinal double dx = currentTarget.getX() - this.mob.getX();\n\t\t\tfinal double dz = currentTarget.getZ() - this.mob.getZ();\n\t\t\tfinal double horizontalDistanceSqr = dx * dx + dz * dz;\n\t\t\tfinal boolean canSee = this.mob.getSensing().hasLineOfSight(currentTarget);\n\t\t\tfinal double preferredMaxRange = getPreferredMaximumRange(this.extraGolem);\n\n\t\t\tif (horizontalDistanceSqr > preferredMaxRange * preferredMaxRange || !canSee) {\n\t\t\t\t// Keep chasing even while the independent ranged timer continues firing.\n\t\t\t\tthis.mob.getNavigation().moveTo(currentTarget, CHASE_SPEED);\n\t\t\t} else {\n\t\t\t\t// No minimum spacing, no retreat, no side-to-side strafe.\n\t\t\t\tthis.mob.getNavigation().stop();\n\t\t\t}\n\t\t}\n\t}\n'''
text = text[:start_i] + new_goal + text[end_i:]

shoot_path.write_text(text)

final = shoot_path.read_text()
for required in (
    'DEFAULT_PREFERRED_MAX_RANGE = 15.0D',
    'POTION_PREFERRED_MAX_RANGE = 10.0D',
    'hasCompartmentContents(this.extraGolem)',
    'horizontalDistanceSqr > preferredMaxRange * preferredMaxRange',
    'this.mob.getNavigation().moveTo(currentTarget, CHASE_SPEED);',
    'No warmup and no maximum firing-distance gate',
    'data.hasRangedShotCooldownElapsed(gameTime, getAttackInterval())',
    'new ThrownSplashPotion',
    'new ThrownLingeringPotion',
    'itemStack.is(Items.SPLASH_POTION)',
    'itemStack.is(Items.LINGERING_POTION)',
):
    if required not in final:
        raise SystemExit(f'Missing pass15 invariant: {required}')
for forbidden in (
    'RANGED_WARMUP_TICKS',
    'PREFERRED_MIN_RANGE',
    'COMBAT_STRAFE_SPEED',
    'getMoveControl().strafe',
    'WARDEN_HORIZONTAL_RANGE_SQR',
    'WARDEN_VERTICAL_RANGE',
):
    if forbidden in final:
        raise SystemExit(f'Obsolete pass14 behavior still present: {forbidden}')

print('Applied pass 15: ranged-only when compartment non-empty; 15-block max (10 for potions), no warmup/strafe/min-range, fire while chasing at any target distance.')
