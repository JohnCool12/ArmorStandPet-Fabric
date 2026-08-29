from pathlib import Path
import re

ROOT = Path('project/src/main/java')

# ---- Broad, documented 26.1 renames ----
for p in ROOT.rglob('*.java'):
    s = p.read_text()
    original = s
    s = s.replace('.isDay()', '.isBrightOutside()')
    s = s.replace('.isNight()', '.isDarkOutside()')
    s = s.replace('.isInWaterRainOrBubble()', '.isInWaterOrRain()')
    s = s.replace('IntProvider.NON_NEGATIVE_CODEC', 'IntProviders.NON_NEGATIVE_CODEC')
    s = s.replace('IntProvider.POSITIVE_CODEC', 'IntProviders.POSITIVE_CODEC')
    s = s.replace('IntProvider.codec(', 'IntProviders.codec(')
    if 'IntProviders.' in s and 'import net.minecraft.util.valueproviders.IntProviders;' not in s:
        if 'import net.minecraft.util.valueproviders.IntProvider;\n' in s:
            s = s.replace('import net.minecraft.util.valueproviders.IntProvider;\n',
                          'import net.minecraft.util.valueproviders.IntProvider;\nimport net.minecraft.util.valueproviders.IntProviders;\n')
        else:
            # Insert with other minecraft imports.
            marker = 'import net.minecraft.'
            idx = s.find(marker)
            if idx >= 0:
                s = s[:idx] + 'import net.minecraft.util.valueproviders.IntProviders;\n' + s[idx:]
    if s != original:
        p.write_text(s)

# IntProvider equality helpers were removed. Preserve semantic equality by comparing the provider itself.
p = ROOT / 'com/mcmoddev/golems/data/behavior/util/TargetedMobEffects.java'
if p.exists():
    s = p.read_text()
    s = s.replace(
        '&& rolls.getType() == that.rolls.getType() && rolls.getMinValue() == that.rolls.getMinValue() && rolls.getMaxValue() == this.rolls.getMaxValue()\n\t\t\t\t&& effects.equals(that.effects);',
        '&& rolls.equals(that.rolls) && effects.equals(that.effects);')
    s = s.replace(
        'return Objects.hash(targetType, radius, rolls.getType(), rolls.getMinValue(), rolls.getMaxValue(), effects);',
        'return Objects.hash(targetType, radius, rolls, effects);')
    if 'net.minecraft.server.level.ServerLevel' not in s:
        s = s.replace('import net.minecraft.util.valueproviders.IntProviders;\n',
                      'import net.minecraft.util.valueproviders.IntProviders;\nimport net.minecraft.server.level.ServerLevel;\n')
    old = '''\t\t\t\tList<LivingEntity> targets = mob.level().getNearbyEntities(LivingEntity.class,\n\t\t\t\t\t\tcondition, mob, mob.getBoundingBox().inflate(radius));\n\t\t\t\t// apply to each entity in list\n\t\t\t\tfor (LivingEntity target : targets) {\n\t\t\t\t\tcopyEffects(target, rolls, effects);\n\t\t\t\t}'''
    new = '''\t\t\t\tif (mob.level() instanceof ServerLevel serverLevel) {\n\t\t\t\t\tList<LivingEntity> targets = serverLevel.getNearbyEntities(LivingEntity.class,\n\t\t\t\t\t\t\tcondition, mob, mob.getBoundingBox().inflate(radius));\n\t\t\t\t\t// apply to each entity in list\n\t\t\t\t\tfor (LivingEntity target : targets) {\n\t\t\t\t\t\tcopyEffects(target, rolls, effects);\n\t\t\t\t\t}\n\t\t\t\t}'''
    s = s.replace(old, new)
    p.write_text(s)

# Registry#getOrThrow(ResourceKey) now returns a Holder.Reference.
p = ROOT / 'com/mcmoddev/golems/data/model/LayerList.java'
if p.exists():
    s = p.read_text().replace('LayerList layerList = registry.getOrThrow(key);',
                              'LayerList layerList = registry.getOrThrow(key).value();')
    p.write_text(s)

# Built-in registry Identifier lookup now has an explicit value helper.
for rel in [
    'com/mcmoddev/golems/data/DeferredBlockState.java',
    'com/mcmoddev/golems/data/golem/DeferredBlockState.java',
    'com/mcmoddev/golems/data/behavior/util/DeferredBlockState.java',
]:
    p = ROOT / rel
    if p.exists():
        s = p.read_text().replace('BuiltInRegistries.BLOCK.get(this.block)', 'BuiltInRegistries.BLOCK.getValue(this.block)')
        p.write_text(s)

# EntityType.Builder#build now takes a ResourceKey<EntityType<?>>.
p = ROOT / 'com/mcmoddev/golems/EGRegistry.java'
if p.exists():
    s = p.read_text().replace(
        '.build("golem"));',
        '.build(ResourceKey.create(net.minecraft.core.registries.Registries.ENTITY_TYPE, Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "golem"))));')
    p.write_text(s)

# UtilityBlock was affected by the block callback signature overhaul. Keep its exact old semantics:
# invisible, non-colliding, replaceable, waterloggable, no fall/inside effects.
p = ROOT / 'com/mcmoddev/golems/block/UtilityBlock.java'
if p.exists():
    p.write_text('''package com.mcmoddev.golems.block;\n\nimport net.minecraft.core.BlockPos;\nimport net.minecraft.core.Direction;\nimport net.minecraft.server.level.ServerLevel;\nimport net.minecraft.util.RandomSource;\nimport net.minecraft.world.entity.Entity;\nimport net.minecraft.world.entity.InsideBlockEffectApplier;\nimport net.minecraft.world.item.ItemStack;\nimport net.minecraft.world.item.context.BlockPlaceContext;\nimport net.minecraft.world.level.BlockGetter;\nimport net.minecraft.world.level.Level;\nimport net.minecraft.world.level.LevelAccessor;\nimport net.minecraft.world.level.LevelReader;\nimport net.minecraft.world.level.ScheduledTickAccess;\nimport net.minecraft.world.level.block.Block;\nimport net.minecraft.world.level.block.Blocks;\nimport net.minecraft.world.level.block.RenderShape;\nimport net.minecraft.world.level.block.SimpleWaterloggedBlock;\nimport net.minecraft.world.level.block.state.BlockState;\nimport net.minecraft.world.level.block.state.StateDefinition;\nimport net.minecraft.world.level.block.state.properties.BlockStateProperties;\nimport net.minecraft.world.level.block.state.properties.BooleanProperty;\nimport net.minecraft.world.level.material.FluidState;\nimport net.minecraft.world.level.material.Fluids;\nimport net.minecraft.world.phys.shapes.CollisionContext;\nimport net.minecraft.world.phys.shapes.Shapes;\nimport net.minecraft.world.phys.shapes.VoxelShape;\n\npublic abstract class UtilityBlock extends Block implements SimpleWaterloggedBlock {\n    public static final BooleanProperty WATERLOGGED = BlockStateProperties.WATERLOGGED;\n    protected final int tickRate;\n\n    public UtilityBlock(final Properties prop, final int tickrate) {\n        super(prop.strength(-1F).noCollision().randomTicks());\n        this.registerDefaultState(this.stateDefinition.any().setValue(WATERLOGGED, false));\n        this.tickRate = tickrate;\n    }\n\n    protected boolean remove(final Level level, final BlockState state, final BlockPos pos, final int flag) {\n        final BlockState replaceWith = state.getValue(WATERLOGGED)\n                ? Fluids.WATER.getSource().defaultFluidState().createLegacyBlock()\n                : Blocks.AIR.defaultBlockState();\n        return level.setBlock(pos, replaceWith, flag);\n    }\n\n    @Override\n    protected void createBlockStateDefinition(final StateDefinition.Builder<Block, BlockState> builder) {\n        builder.add(WATERLOGGED);\n    }\n\n    @Override\n    protected FluidState getFluidState(final BlockState state) {\n        return state.getValue(WATERLOGGED) ? Fluids.WATER.getSource(false) : super.getFluidState(state);\n    }\n\n    @Override\n    protected void onPlace(final BlockState state, final Level level, final BlockPos pos, final BlockState oldState, final boolean isMoving) {\n        if (this.isRandomlyTicking(state)) {\n            level.scheduleTick(pos, this, tickRate);\n            if (state.getValue(WATERLOGGED)) {\n                level.scheduleTick(pos, Fluids.WATER, Fluids.WATER.getTickDelay(level));\n            }\n            level.updateNeighborsAt(pos, this);\n        }\n    }\n\n    @Override\n    protected void tick(final BlockState state, final ServerLevel level, final BlockPos pos, final RandomSource rand) {\n        super.tick(state, level, pos, rand);\n        if (this.isRandomlyTicking(state)) {\n            level.scheduleTick(pos, this, tickRate);\n            if (state.getValue(WATERLOGGED)) {\n                level.scheduleTick(pos, Fluids.WATER, Fluids.WATER.getTickDelay(level));\n            }\n        }\n    }\n\n    @Override\n    protected BlockState updateShape(BlockState state, LevelReader level, ScheduledTickAccess ticks, BlockPos pos,\n                                     Direction directionToNeighbour, BlockPos neighbourPos, BlockState neighbourState,\n                                     RandomSource random) {\n        if (state.getValue(WATERLOGGED)) {\n            ticks.scheduleTick(pos, Fluids.WATER, Fluids.WATER.getTickDelay(level));\n        }\n        return super.updateShape(state, level, ticks, pos, directionToNeighbour, neighbourPos, neighbourState, random);\n    }\n\n    @Override\n    protected VoxelShape getShape(final BlockState state, final BlockGetter level, final BlockPos pos, final CollisionContext cxt) {\n        return state.getValue(WATERLOGGED) ? Blocks.WATER.defaultBlockState().getShape(level, pos, cxt) : Shapes.empty();\n    }\n\n    @Override\n    protected ItemStack getCloneItemStack(final LevelReader level, final BlockPos pos, final BlockState state, final boolean includeData) {\n        return ItemStack.EMPTY;\n    }\n\n    @Override\n    protected boolean canBeReplaced(final BlockState state, final BlockPlaceContext useContext) {\n        return true;\n    }\n\n    @Override\n    protected RenderShape getRenderShape(final BlockState state) {\n        return RenderShape.INVISIBLE;\n    }\n\n    @Override\n    public void fallOn(final Level level, final BlockState state, final BlockPos pos, final Entity entity, final double fallDistance) {\n        // Intentionally no fall effect.\n    }\n\n    @Override\n    protected void entityInside(final BlockState state, final Level level, final BlockPos pos, final Entity entity,\n                                final InsideBlockEffectApplier effectApplier, final boolean isPrecise) {\n        // Intentionally no inside-block effect.\n    }\n\n    @Override\n    public void updateEntityMovementAfterFallOn(final BlockGetter level, final Entity entity) {\n        // Intentionally no movement modification.\n    }\n\n    @Override\n    public boolean isPossibleToRespawnInThis(final BlockState state) {\n        return true;\n    }\n}\n''')

# Command argument/permission migration. Keep the same op-level-2 requirement.
p = ROOT / 'com/mcmoddev/golems/network/SummonGolemCommand.java'
if p.exists():
    s = p.read_text()
    s = s.replace('import net.minecraft.commands.arguments.ResourceLocationArgument;',
                  'import net.minecraft.commands.arguments.IdentifierArgument;')
    s = s.replace('ResourceLocationArgument.id()', 'IdentifierArgument.id()')
    s = s.replace('ResourceLocationArgument.getId(', 'IdentifierArgument.getId(')
    s = s.replace('.requires(p -> p.hasPermission(2))', '.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))')
    s = s.replace('entity.moveTo(pos.getX() + 0.5D, pos.getY(), pos.getZ() + 0.5D);',
                  'entity.snapTo(pos.getX() + 0.5D, pos.getY(), pos.getZ() + 0.5D, entity.getYRot(), entity.getXRot());')
    p.write_text(s)

# Player permission API changed from integer methods to PermissionSet.
p = ROOT / 'com/mcmoddev/golems/network/ServerBoundSpawnGolemPacket.java'
if p.exists():
    s = p.read_text()
    if 'import net.minecraft.server.permissions.Permission;' not in s:
        s = s.replace('import net.minecraft.server.level.ServerPlayer;\n',
                      'import net.minecraft.server.level.ServerPlayer;\nimport net.minecraft.server.permissions.Permission;\nimport net.minecraft.server.permissions.PermissionLevel;\n')
    s = s.replace('!player.hasPermissions(ExtraGolems.CONFIG.debugPermissionLevel())',
                  '!player.permissions().hasPermission(new Permission.HasCommandLevel(PermissionLevel.byId(ExtraGolems.CONFIG.debugPermissionLevel())))')
    s = s.replace('player.displayClientMessage(Component.translatable("command.golem.success", id, (int) player.getX(),\n                        (int) player.getY(), (int) player.getZ()), false);',
                  'player.sendSystemMessage(Component.translatable("command.golem.success", id, (int) player.getX(),\n                        (int) player.getY(), (int) player.getZ()));')
    p.write_text(s)

# Spawn helpers: ServerLevel owns difficulty calculation and Entity movement uses snapTo.
p = ROOT / 'com/mcmoddev/golems/item/SpawnGolemItem.java'
if p.exists():
    s = p.read_text()
    s = s.replace('entity.moveTo(spawnPos.getX(), spawnPos.getY(), spawnPos.getZ());',
                  'entity.snapTo(spawnPos.getX(), spawnPos.getY(), spawnPos.getZ(), entity.getYRot(), entity.getXRot());')
    s = s.replace('entity.finalizeSpawn((ServerLevel) level, level.getCurrentDifficultyAt(spawnPos),',
                  'entity.finalizeSpawn((ServerLevel) level, ((ServerLevel) level).getCurrentDifficultyAt(spawnPos),')
    p.write_text(s)

# Item#getDescriptionId no longer takes a stack.
p = ROOT / 'com/mcmoddev/golems/item/GolemSpellItem.java'
if p.exists():
    s = p.read_text().replace('this.getDescriptionId(stack)', 'this.getDescriptionId()')
    p.write_text(s)

# Snow-golem construction uses the same explicit spawn reason / snap API as iron golems.
p = ROOT / 'com/mcmoddev/golems/block/GolemHeadBlock.java'
if p.exists():
    s = p.read_text()
    s = s.replace('EntityType.SNOW_GOLEM.create(level)', 'EntityType.SNOW_GOLEM.create(level, EntitySpawnReason.MOB_SUMMONED)')
    s = re.sub(r'(snowGolem|snowman)\.moveTo\(([^;]+)\);', r'\1.snapTo(\2, \1.getYRot(), \1.getXRot());', s)
    p.write_text(s)

print('Applied Extra Golems 26.1 migration stage 2')
