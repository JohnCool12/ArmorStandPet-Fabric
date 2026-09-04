from pathlib import Path

root = Path("project")

data_path = root / "src/main/java/com/mcmoddev/golems/data/behavior/data/ShootBehaviorData.java"
text = data_path.read_text()

text = text.replace(
    "import net.minecraft.nbt.CompoundTag;\nimport net.minecraft.world.entity.ai.goal.MeleeAttackGoal;",
    "import net.minecraft.nbt.CompoundTag;\nimport net.minecraft.world.entity.LivingEntity;\nimport net.minecraft.world.entity.ai.goal.MeleeAttackGoal;\nimport org.jetbrains.annotations.Nullable;"
)

old = """\tprivate final RangedAttackGoal rangedAttackGoal;\n\tprivate final MeleeAttackGoal meleeAttackGoal;\n"""
new = """\tprivate final RangedAttackGoal rangedAttackGoal;\n\tprivate final MeleeAttackGoal meleeAttackGoal;\n\n\t// Per-golem state for the Warden-style ranged fallback used by the dispenser golem.\n\tprivate @Nullable LivingEntity trackedTarget;\n\tprivate long targetAcquiredGameTime = Long.MIN_VALUE;\n\tprivate long lastAttackGameTime = Long.MIN_VALUE;\n"""
if old not in text:
    raise SystemExit("ShootBehaviorData field insertion point not found")
text = text.replace(old, new, 1)

marker = """\tpublic int getAmmo() {\n\t\treturn this.entity.getAmmo();\n\t}\n\n\t//// NBT ////\n"""
insert = """\tpublic int getAmmo() {\n\t\treturn this.entity.getAmmo();\n\t}\n\n\t//// WARDEN-STYLE RANGED FALLBACK ////\n\n\tpublic void trackTarget(final @Nullable LivingEntity target, final long gameTime) {\n\t\tif (target != this.trackedTarget) {\n\t\t\tthis.trackedTarget = target;\n\t\t\tthis.targetAcquiredGameTime = target == null ? Long.MIN_VALUE : gameTime;\n\t\t}\n\t}\n\n\tpublic boolean hasTrackedTargetFor(final long gameTime, final long ticks) {\n\t\treturn this.trackedTarget != null\n\t\t\t\t&& this.targetAcquiredGameTime != Long.MIN_VALUE\n\t\t\t\t&& gameTime - this.targetAcquiredGameTime >= ticks;\n\t}\n\n\tpublic void markAttack(final long gameTime) {\n\t\tthis.lastAttackGameTime = gameTime;\n\t}\n\n\tpublic boolean hasAttackCooldownElapsed(final long gameTime, final long ticks) {\n\t\treturn this.lastAttackGameTime == Long.MIN_VALUE || gameTime - this.lastAttackGameTime >= ticks;\n\t}\n\n\t//// NBT ////\n"""
if marker not in text:
    raise SystemExit("ShootBehaviorData getter/NBT insertion point not found")
text = text.replace(marker, insert, 1)
data_path.write_text(text)

shoot_path = root / "src/main/java/com/mcmoddev/golems/data/behavior/ShootArrowsBehavior.java"
text = shoot_path.read_text()

old = """\t/** The amount of damage dealt by arrows **/\n\tprivate final double damage;\n"""
new = """\t/** The amount of damage dealt by arrows **/\n\tprivate final double damage;\n\n\t// Java Warden-style ranged fallback gates.\n\tprivate static final long WARDEN_TARGET_TIME_TICKS = 10L * 20L;\n\tprivate static final long WARDEN_ATTACK_COOLDOWN_TICKS = 5L * 20L;\n\tprivate static final double WARDEN_HORIZONTAL_RANGE_SQR = 15.0D * 15.0D;\n\tprivate static final double WARDEN_VERTICAL_RANGE = 20.0D;\n\tprivate static final double RANGED_DISTANCE_FACTOR_RANGE = 32.0D;\n"""
if old not in text:
    raise SystemExit("ShootArrowsBehavior damage field insertion point not found")
text = text.replace(old, new, 1)

old = """\t@Override\n\tpublic void onAttachData(IExtraGolem entity) {\n\t\tfinal RangedAttackGoal rangedGoal = new RangedAttackGoal(entity.asMob(), 1.0D, getAttackInterval(), 32.0F);\n\t\tfinal MeleeAttackGoal meleeGoal = new MeleeAttackGoal(entity.asMob(), 1.0D, true);\n\t\tentity.attachBehaviorData(new ShootBehaviorData(entity, rangedGoal, meleeGoal));\n\t}\n\n\t@Override\n\tpublic List<Component> createDescriptions(RegistryAccess registryAccess) {\n"""
new = """\t@Override\n\tpublic void onAttachData(IExtraGolem entity) {\n\t\t// Retain a ranged goal object for behavior-data compatibility, but never give it\n\t\t// movement control. The melee goal stays active so pursuit continues while firing.\n\t\tfinal RangedAttackGoal rangedGoal = new RangedAttackGoal(entity.asMob(), 1.0D, getAttackInterval(), 32.0F);\n\t\tfinal MeleeAttackGoal meleeGoal = new MeleeAttackGoal(entity.asMob(), 1.0D, true);\n\t\tentity.attachBehaviorData(new ShootBehaviorData(entity, rangedGoal, meleeGoal));\n\t}\n\n\t@Override\n\tprotected void updateCombatTask(final IExtraGolem entity, final boolean forceMelee) {\n\t\tfinal Mob mob = entity.asMob();\n\t\tgetShootData(entity).ifPresent(data -> {\n\t\t\t// RangedAttackGoal stops advancing once it considers itself in firing range.\n\t\t\t// Keep MeleeAttackGoal in control instead, and fire independently from onTick.\n\t\t\tmob.goalSelector.removeGoal(data.getRangedGoal());\n\t\t\tmob.goalSelector.removeGoal(data.getMeleeGoal());\n\t\t\tmob.goalSelector.addGoal(0, data.getMeleeGoal());\n\t\t});\n\t}\n\n\t@Override\n\tpublic void onTarget(final IExtraGolem entity, final LivingEntity target) {\n\t\tsuper.onTarget(entity, target);\n\t\tfinal long gameTime = entity.asMob().level().getGameTime();\n\t\tgetShootData(entity).ifPresent(data -> data.trackTarget(target, gameTime));\n\t}\n\n\t@Override\n\tpublic void onAttack(final IExtraGolem entity, final net.minecraft.world.entity.Entity target) {\n\t\t// A successful melee hit resets the Warden-style five-second attack gate.\n\t\tfinal long gameTime = entity.asMob().level().getGameTime();\n\t\tgetShootData(entity).ifPresent(data -> data.markAttack(gameTime));\n\t}\n\n\t@Override\n\tpublic void onTick(final IExtraGolem entity) {\n\t\tsuper.onTick(entity);\n\t\tfinal Mob mob = entity.asMob();\n\t\tfinal LivingEntity target = mob.getTarget();\n\t\tfinal long gameTime = mob.level().getGameTime();\n\n\t\tgetShootData(entity).ifPresent(data -> {\n\t\t\tdata.trackTarget(target, gameTime);\n\t\t\tif (target == null || !target.isAlive() || !hasAmmo(entity)) {\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\t// Ranged fire is a fallback while closing distance, never a point-blank\n\t\t\t// replacement for the golem's normal melee attack.\n\t\t\tif (isInRangeToAttack(entity, target)) {\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\tfinal double dx = target.getX() - mob.getX();\n\t\t\tfinal double dz = target.getZ() - mob.getZ();\n\t\t\tfinal double dy = Math.abs(target.getY() - mob.getY());\n\t\t\tif (dx * dx + dz * dz > WARDEN_HORIZONTAL_RANGE_SQR || dy > WARDEN_VERTICAL_RANGE) {\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\tif (!data.hasTrackedTargetFor(gameTime, WARDEN_TARGET_TIME_TICKS)\n\t\t\t\t\t|| !data.hasAttackCooldownElapsed(gameTime, WARDEN_ATTACK_COOLDOWN_TICKS)) {\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\t// A sonic boom can pass through blocks; an arrow cannot. Preserve the\n\t\t\t// line-of-sight requirement so the dispenser does not waste ammunition.\n\t\t\tif (!mob.getSensing().hasLineOfSight(target)) {\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\tfinal float distanceFactor = (float) Math.max(0.1D, Math.min(1.0D,\n\t\t\t\t\tMath.sqrt(mob.distanceToSqr(target)) / RANGED_DISTANCE_FACTOR_RANGE));\n\t\t\tif (performRangedAttack(entity, target, distanceFactor)) {\n\t\t\t\tif (consume()) {\n\t\t\t\t\tentity.getInventory().setChanged();\n\t\t\t\t}\n\t\t\t\tdata.markAttack(gameTime);\n\t\t\t}\n\t\t});\n\t}\n\n\t@Override\n\tpublic List<Component> createDescriptions(RegistryAccess registryAccess) {\n"""
if old not in text:
    raise SystemExit("ShootArrowsBehavior method insertion point not found")
text = text.replace(old, new, 1)
shoot_path.write_text(text)

print("Applied pass 13: Dispenser Golem Warden-style ranged fallback with uninterrupted pursuit")
