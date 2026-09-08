from pathlib import Path
import re

root = Path('project')
java = root / 'src/main/java'

def f(rel): return java / rel

def edit(rel, func):
    p=f(rel); s=p.read_text(); n=func(s); p.write_text(n)

def reps(rel, pairs):
    edit(rel, lambda s: _reps(s,pairs))

def _reps(s,pairs):
    for a,b in pairs: s=s.replace(a,b)
    return s

props=root/'gradle.properties'
p=props.read_text().replace('neo_version=26.1.2.94','neo_version=26.1.2.95')
props.write_text(p)

for pth in java.rglob('*.java'):
    s=pth.read_text()
    s=re.sub(r'\.isClientSide\b(?!\s*\()', '.isClientSide()', s)
    s=re.sub(r'\.random\b', '.getRandom()', s)
    s=s.replace('.location()', '.identifier()')
    s=s.replace('.noCollission()', '.noCollision()')
    pth.write_text(s)

reps('com/mcmoddev/golems/EGEvents.java', [('registry.getOrCreateTag(VILLAGER_SUMMONABLE)\n\t\t\t\t\t.getRandomElement(random)', 'registry.getRandomElementOf(VILLAGER_SUMMONABLE, random)')])
reps('com/mcmoddev/golems/EGRegistry.java', [('.sized(1.4F, 2.7F)\n\t\t\t\t\t\t.build("golem"))', '.sized(1.4F, 2.7F)\n\t\t\t\t\t\t.build(ResourceKey.create(Registries.ENTITY_TYPE, Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "golem"))))')])
edit('com/mcmoddev/golems/EGRegistry.java', lambda s: s if 'import net.minecraft.resources.ResourceKey;' in s else s.replace('import net.minecraft.resources.Identifier;','import net.minecraft.resources.Identifier;\nimport net.minecraft.resources.ResourceKey;'))
edit('com/mcmoddev/golems/EGRegistry.java', lambda s: s if 'import net.minecraft.core.registries.Registries;' in s else s.replace('import net.minecraft.core.registries.BuiltInRegistries;','import net.minecraft.core.registries.BuiltInRegistries;\nimport net.minecraft.core.registries.Registries;'))

reps('com/mcmoddev/golems/block/GolemHeadBlock.java', [('EntityType.SNOW_GOLEM.create(level)', 'EntityType.SNOW_GOLEM.create(level, EntitySpawnReason.MOB_SUMMONED)'),('EntityType.IRON_GOLEM.create(level)', 'EntityType.IRON_GOLEM.create(level, EntitySpawnReason.MOB_SUMMONED)'),('.moveTo(spawnX, spawnY, spawnZ, 0.0F, 0.0F)', '.snapTo(spawnX, spawnY, spawnZ, 0.0F, 0.0F)'),('level.getCurrentDifficultyAt(headPos)', '((ServerLevel) level).getCurrentDifficultyAt(headPos)')])

utility = '''package com.mcmoddev.golems.block;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.ScheduledTickAccess;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.SimpleWaterloggedBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.level.material.FluidState;
import net.minecraft.world.level.material.Fluids;
import net.minecraft.world.level.block.entity.InsideBlockEffectApplier;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

public abstract class UtilityBlock extends Block implements SimpleWaterloggedBlock {
    public static final BooleanProperty WATERLOGGED = BlockStateProperties.WATERLOGGED;
    protected final int tickRate;
    public UtilityBlock(final Properties prop, final int tickrate) { super(prop.strength(-1F).noCollision().randomTicks()); this.registerDefaultState(this.stateDefinition.any().setValue(WATERLOGGED, false)); this.tickRate = tickrate; }
    protected boolean remove(final Level level, final BlockState state, final BlockPos pos, final int flag) { final BlockState replaceWith = state.getValue(WATERLOGGED) ? Fluids.WATER.getSource().defaultFluidState().createLegacyBlock() : Blocks.AIR.defaultBlockState(); return level.setBlock(pos, replaceWith, flag); }
    @Override protected void createBlockStateDefinition(final StateDefinition.Builder<Block, BlockState> builder) { builder.add(WATERLOGGED); }
    @Override public FluidState getFluidState(final BlockState state) { return state.getValue(WATERLOGGED) ? Fluids.WATER.getSource(false) : super.getFluidState(state); }
    @Override public void onPlace(final BlockState state, final Level level, final BlockPos pos, final BlockState oldState, final boolean isMoving) { if (this.isRandomlyTicking(state)) { level.scheduleTick(pos, this, tickRate); if (state.getValue(WATERLOGGED)) level.scheduleTick(pos, Fluids.WATER, Fluids.WATER.getTickDelay(level)); level.updateNeighborsAt(pos, this); } }
    @Override public void tick(final BlockState state, final ServerLevel level, final BlockPos pos, final RandomSource rand) { super.tick(state, level, pos, rand); if (this.isRandomlyTicking(state)) { level.scheduleTick(pos, this, tickRate); if (state.getValue(WATERLOGGED)) level.scheduleTick(pos, Fluids.WATER, Fluids.WATER.getTickDelay(level)); } }
    @Override protected BlockState updateShape(BlockState state, LevelReader level, ScheduledTickAccess tickAccess, BlockPos pos, Direction direction, BlockPos neighborPos, BlockState neighborState, RandomSource random) { if (state.getValue(WATERLOGGED)) tickAccess.scheduleTick(pos, Fluids.WATER, Fluids.WATER.getTickDelay(level)); return super.updateShape(state, level, tickAccess, pos, direction, neighborPos, neighborState, random); }
    @Override protected VoxelShape getShape(final BlockState state, final BlockGetter level, final BlockPos pos, final CollisionContext cxt) { return state.getValue(WATERLOGGED) ? Blocks.WATER.defaultBlockState().getShape(level, pos, cxt) : Shapes.empty(); }
    @Override protected ItemStack getCloneItemStack(final LevelReader level, final BlockPos pos, final BlockState state, final boolean includeData) { return ItemStack.EMPTY; }
    @Override protected boolean canBeReplaced(final BlockState state, final BlockPlaceContext useContext) { return true; }
    @Override protected RenderShape getRenderShape(final BlockState state) { return RenderShape.INVISIBLE; }
    @Override protected void fallOn(final Level level, final BlockState state, final BlockPos pos, final Entity entity, final double fallDistance) { }
    @Override protected void entityInside(final BlockState state, final Level level, final BlockPos pos, final Entity entity, InsideBlockEffectApplier applier, boolean canApplyEffects) { }
    @Override protected boolean isPossibleToRespawnInThis(BlockState state) { return true; }
}
'''
f('com/mcmoddev/golems/block/UtilityBlock.java').write_text(utility)

for rel in ['com/mcmoddev/golems/data/behavior/AoeGrowBehavior.java','com/mcmoddev/golems/data/behavior/SetFireBehavior.java','com/mcmoddev/golems/data/behavior/util/TargetedMobEffects.java','com/mcmoddev/golems/data/behavior/util/UpdateTarget.java']:
    edit(rel, lambda s: s.replace('IntProvider.NON_NEGATIVE_CODEC','IntProviders.NON_NEGATIVE_CODEC').replace('IntProvider.codec(','IntProviders.codec(').replace('.getMinValue()','.minInclusive()').replace('.getMaxValue()','.maxInclusive()').replace('.getType()','.codec()'))
    edit(rel, lambda s: s if 'IntProviders' not in s or 'import net.minecraft.util.valueproviders.IntProviders;' in s else s.replace('import net.minecraft.util.valueproviders.IntProvider;','import net.minecraft.util.valueproviders.IntProvider;\nimport net.minecraft.util.valueproviders.IntProviders;'))

reps('com/mcmoddev/golems/data/behavior/AbstractShootBehavior.java', [('tag.getInt(KEY_AMMO)','tag.getIntOr(KEY_AMMO, 0)'), ('!mob.canAttackType(e.getType())','!(e instanceof LivingEntity living) || !mob.canAttack(living)')])
reps('com/mcmoddev/golems/data/behavior/ExplodeBehavior.java', [('tag.getCompound(KEY_EXPLOSION_HELPER)','tag.getCompoundOrEmpty(KEY_EXPLOSION_HELPER)')])
reps('com/mcmoddev/golems/data/behavior/UseFuelBehavior.java', [('tag.getCompound(KEY_FUEL_HELPER)','tag.getCompoundOrEmpty(KEY_FUEL_HELPER)')])
reps('com/mcmoddev/golems/data/behavior/data/ExplodeBehaviorData.java', [('tag.getInt(KEY_FUSE)','tag.getIntOr(KEY_FUSE, 0)'),('tag.getBoolean(KEY_FUSE_LIT)','tag.getBooleanOr(KEY_FUSE_LIT, false)')])
reps('com/mcmoddev/golems/data/behavior/data/UseFuelBehaviorData.java', [('tag.getInt(KEY_FUEL)','tag.getIntOr(KEY_FUEL, 0)')])
reps('com/mcmoddev/golems/data/behavior/ItemUpdateGolemBehavior.java', [('item.getItemHolder()','item.getItem().builtInRegistryHolder()'),('randomItem.getDescription()','randomItem.getName(new ItemStack(randomItem))')])
reps('com/mcmoddev/golems/data/behavior/TemptBehavior.java', [('Ingredient ingredient = holderSet.unwrap().map(Ingredient::of, list -> Ingredient.of(list.stream().map(Holder::value).toArray(Item[]::new)));','Ingredient ingredient = Ingredient.of(holderSet);'),('randomItem.getDescription()','randomItem.getName(new ItemStack(randomItem))')])
for rel in ['com/mcmoddev/golems/data/behavior/SetFireBehavior.java','com/mcmoddev/golems/data/behavior/util/TargetedMobEffects.java']:
    edit(rel, lambda s: re.sub(r'(\w+)\.level\(\)\.getNearbyEntities\(LivingEntity\.class,\s*condition,\s*\w+,\s*(\w+)\.getBoundingBox\(\)\.inflate\(radius\)\)', r'\1.level().getEntities(net.minecraft.world.level.entity.EntityTypeTest.forClass(LivingEntity.class), \2.getBoundingBox().inflate(radius), target -> condition.test(\2, target))', s))
reps('com/mcmoddev/golems/data/behavior/ShootSnowballsBehavior.java', [('new Snowball(mob.level(), mob)','new Snowball(mob.level(), mob, new ItemStack(Items.SNOWBALL))')])
edit('com/mcmoddev/golems/data/behavior/ShootSnowballsBehavior.java', lambda s: s if 'import net.minecraft.world.item.Items;' in s else s.replace('import net.minecraft.world.entity.projectile.throwableitemprojectile.Snowball;','import net.minecraft.world.entity.projectile.throwableitemprojectile.Snowball;\nimport net.minecraft.world.item.ItemStack;\nimport net.minecraft.world.item.Items;'))
reps('com/mcmoddev/golems/data/behavior/SplitBehavior.java', [('mob.level().getCurrentDifficultyAt(mob.blockPosition())','serverLevel.getCurrentDifficultyAt(mob.blockPosition())')])
reps('com/mcmoddev/golems/data/behavior/SummonBehavior.java', [('TagParser.parseTag(this.nbt)','TagParser.parseCompoundFully(this.nbt)'),('EntityType.create(tag, self.level()).ifPresent(e -> {','java.util.Optional.ofNullable(EntityType.loadEntityRecursive(tag, self.level(), EntitySpawnReason.MOB_SUMMONED, e -> e)).ifPresent(e -> {'),('mob.setPersistentAngerTarget(target.getUUID());','mob.setPersistentAngerTarget(net.minecraft.world.entity.EntityReference.of(target.getUUID()));')])

def patch_fuel(s):
    s=s.replace('int burnTime = stack.getBurnTime(RecipeType.SMELTING) * (player.isCrouching() ? stack.getCount() : 1);','int burnTime = mob.level().fuelValues().burnDuration(stack) * (player.isCrouching() ? stack.getCount() : 1);')
    s=s.replace('stack = stack.getCraftingRemainingItem();','stack = craftingRemainder(stack);').replace('player.setItemInHand(hand, stack.getCraftingRemainingItem());','player.setItemInHand(hand, craftingRemainder(stack));')
    if 'private static ItemStack craftingRemainder' not in s: s=s.replace('\n\t//// EQUALITY ////','\n\tprivate static ItemStack craftingRemainder(ItemStack stack) { final net.minecraft.world.item.ItemStackTemplate template = stack.getItem().getCraftingRemainder(); return template == null ? ItemStack.EMPTY : template.create(); }\n\n\t//// EQUALITY ////')
    return s
edit('com/mcmoddev/golems/data/behavior/UseFuelBehavior.java', patch_fuel)
reps('com/mcmoddev/golems/data/behavior/WearBannerBehavior.java', [('mob.spawnAtLocation(banner, mob.getBbHeight() * 0.9F);','if (mob.level() instanceof ServerLevel serverLevel) mob.spawnAtLocation(serverLevel, banner, mob.getBbHeight() * 0.9F);')])
edit('com/mcmoddev/golems/data/behavior/WearBannerBehavior.java', lambda s: s if 'import net.minecraft.server.level.ServerLevel;' in s else s.replace('import net.minecraft.world.entity.EquipmentSlot;','import net.minecraft.server.level.ServerLevel;\nimport net.minecraft.world.entity.EquipmentSlot;'))
reps('com/mcmoddev/golems/data/golem/BuildingBlocks.java', [('BuiltInRegistries.BLOCK.get(this.block)','BuiltInRegistries.BLOCK.getValue(this.block)')])
reps('com/mcmoddev/golems/util/DeferredBlockState.java', [('BuiltInRegistries.BLOCK.get(this.block)','BuiltInRegistries.BLOCK.getValue(this.block)')])
reps('com/mcmoddev/golems/data/model/LayerList.java', [('registry.getOrThrow(key)','registry.getValueOrThrow(key)')])
reps('com/mcmoddev/golems/util/DeferredHolderSet.java', [('registry.getOrCreateTag(either.left().get())','registry.getOrThrow(either.left().get())'),('registry.getHolder(key)','registry.get(key)')])
reps('com/mcmoddev/golems/data/model/Layer.java', [('Vec3.fromRGB24(color)','new Vec3(((color >> 16) & 255) / 255.0D, ((color >> 8) & 255) / 255.0D, (color & 255) / 255.0D)')])
edit('com/mcmoddev/golems/data/golem/Attributes.java', lambda s: s.replace('.getHolderOrThrow(', '.getOrThrow('))
reps('com/mcmoddev/golems/entity/goal/InertGoal.java', [('neutralMob.setRemainingPersistentAngerTime(0);','neutralMob.stopBeingAngry();')])
reps('com/mcmoddev/golems/entity/goal/MoveToItemGoal.java', [('mob.wantsToPickUp(item.getItem())','mob.wantsToPickUp((ServerLevel) mob.level(), item.getItem())')])
edit('com/mcmoddev/golems/entity/goal/MoveToItemGoal.java', lambda s: s if 'import net.minecraft.server.level.ServerLevel;' in s else s.replace('import net.minecraft.world.entity.Mob;','import net.minecraft.server.level.ServerLevel;\nimport net.minecraft.world.entity.Mob;'))
reps('com/mcmoddev/golems/item/GolemSpellItem.java', [('getDescriptionId(stack)','getDescriptionId()')])
reps('com/mcmoddev/golems/item/GuideBookItem.java', [('playerIn.getCommandSenderWorld()','playerIn.level()')])
reps('com/mcmoddev/golems/item/SpawnGolemItem.java', [('entity.moveTo(spawnPos.getX(), spawnPos.getY(), spawnPos.getZ());','entity.snapTo(spawnPos.getX(), spawnPos.getY(), spawnPos.getZ());'),('level.getCurrentDifficultyAt(spawnPos)','((ServerLevel) level).getCurrentDifficultyAt(spawnPos)')])

def patch_i(s):
    s=s.replace('import net.minecraft.nbt.Tag;\n','').replace('import net.minecraft.world.inventory.ContainerListener;\n','').replace('IInventoryProvider, ContainerListener, RangedAttackMob', 'IInventoryProvider, RangedAttackMob').replace('import net.minecraft.nbt.CompoundTag;','import net.minecraft.world.level.storage.ValueInput;\nimport net.minecraft.world.level.storage.ValueOutput;')
    start=s.index('\tdefault void writeContainer('); end=s.index('\n\t}', s.index('\tdefault void readContainer(',start))+4
    new='\tdefault void writeContainer(ValueOutput output) {\n\t\tgetGolemId().ifPresent(id -> output.putString(KEY_GOLEM_ID, id.toString()));\n\t}\n\n\tdefault void readContainer(ValueInput input) {\n\t\tString id = input.getStringOr(KEY_GOLEM_ID, input.getStringOr("Material", ""));\n\t\tif (!id.isEmpty()) setGolemId(Identifier.parse(id));\n\t}\n'
    return s[:start]+new+s[end:]
edit('com/mcmoddev/golems/entity/IExtraGolem.java', patch_i)

def patch_var(s):
    s=s.replace('import net.minecraft.nbt.CompoundTag;\nimport net.minecraft.nbt.Tag;','import net.minecraft.world.level.storage.ValueInput;\nimport net.minecraft.world.level.storage.ValueOutput;').replace('default void writeVariant(final CompoundTag tag) {\n\t\ttag.putByte(KEY_VARIANT, (byte) getVariant());\n\t}', 'default void writeVariant(final ValueOutput output) {\n\t\toutput.putByte(KEY_VARIANT, (byte) getVariant());\n\t}')
    return re.sub(r'default void readVariant\(final CompoundTag tag\) \{.*?\n\t\}', 'default void readVariant(final ValueInput input) {\n\t\tsetVariant(input.getByteOr(KEY_VARIANT, (byte) 0));\n\t}', s, flags=re.S)
edit('com/mcmoddev/golems/entity/IVariantProvider.java', patch_var)

def patch_golem(s):
    s=s.replace('import net.minecraft.tags.BiomeTags;\n','')
    if 'import net.minecraft.world.attribute.EnvironmentAttributes;' not in s: s=s.replace('import net.minecraft.world.Container;','import net.minecraft.world.Container;\nimport net.minecraft.world.attribute.EnvironmentAttributes;')
    if 'import net.minecraft.world.level.storage.ValueInput;' not in s: s=s.replace('import net.minecraft.world.level.Level;','import net.minecraft.world.level.Level;\nimport net.minecraft.world.level.storage.ValueInput;\nimport net.minecraft.world.level.storage.ValueOutput;')
    if 'import net.minecraft.core.particles.SpellParticleOption;' not in s: s=s.replace('import net.minecraft.core.particles.ParticleTypes;','import net.minecraft.core.particles.ParticleTypes;\nimport net.minecraft.core.particles.SpellParticleOption;')
    if 'import net.minecraft.core.BlockPos;' not in s: s=s.replace('import net.minecraft.core.RegistryAccess;','import net.minecraft.core.RegistryAccess;\nimport net.minecraft.core.BlockPos;')
    s=s.replace('return this.isSunBurnTick();','if (!(level() instanceof ServerLevel serverLevel) || !serverLevel.isBrightOutside()) return false;\n\t\tfloat f = getLightLevelDependentMagicValue();\n\t\tBlockPos pos = BlockPos.containing(getX(), getEyeY(), getZ());\n\t\treturn f > 0.5F && getRandom().nextFloat() * 30.0F < (f - 0.4F) * 2.0F && !isInWaterOrRain() && serverLevel.canSeeSky(pos);')
    s=re.sub(r'@Override\n\tpublic boolean canAttackType\(final EntityType<\?> type\) \{.*?\n\t\}', '@Override\n\tpublic boolean canAttack(final LivingEntity entity) {\n\t\tfinal EntityType<?> type = entity.getType();\n\t\tif (type == EntityType.PLAYER && this.isPlayerCreated()) return ExtraGolems.CONFIG.enableFriendlyFire();\n\t\tif (type == EntityType.VILLAGER || type == EGRegistry.EntityReg.GOLEM.get() || type == EntityType.IRON_GOLEM || type == EntityType.SNOW_GOLEM) return false;\n\t\treturn super.canAttack(entity);\n\t}', s, count=1, flags=re.S)
    s=s.replace('public ItemStack getPickedResult(final HitResult ray)', 'public ItemStack getPickResult()')
    s=re.sub(r'@Override\n\tprotected ResourceKey<net\.minecraft\.world\.level\.storage\.loot\.LootTable> getDefaultLootTable\(\) \{.*?\n\t\}', '@Override\n\tprotected void dropFromLootTable(ServerLevel level, DamageSource source, boolean recentlyHit) {\n\t\tfinal Optional<GolemContainer> c = getContainer();\n\t\tif (c.isEmpty()) { super.dropFromLootTable(level, source, recentlyHit); return; }\n\t\tResourceKey<net.minecraft.world.level.storage.loot.LootTable> key = ResourceKey.create(net.minecraft.core.registries.Registries.LOOT_TABLE, c.get().getLootTable());\n\t\tsuper.dropFromLootTable(level, source, recentlyHit, key);\n\t}', s, count=1, flags=re.S)
    s=s.replace('public void customServerAiStep() {\n\t\tsuper.customServerAiStep();','public void customServerAiStep(ServerLevel serverLevel) {\n\t\tsuper.customServerAiStep(serverLevel);').replace('this.level().getBiome(this.blockPosition()).is(BiomeTags.SNOW_GOLEM_MELTS)', 'serverLevel.environmentAttributes().getValue(EnvironmentAttributes.SNOW_GOLEM_MELTS, this.position())').replace('public boolean isInvulnerableTo(DamageSource pSource) {\n\t\tif (super.isInvulnerableTo(pSource))', 'public boolean isInvulnerableTo(ServerLevel serverLevel, DamageSource pSource) {\n\t\tif (super.isInvulnerableTo(serverLevel, pSource))').replace('public boolean doHurtTarget(Entity target) {\n\t\tif (super.doHurtTarget(target))', 'public boolean doHurtTarget(ServerLevel serverLevel, Entity target) {\n\t\tif (super.doHurtTarget(serverLevel, target))').replace('protected void actuallyHurt(DamageSource source, float amount) {\n\t\tsuper.actuallyHurt(source, amount);', 'protected void actuallyHurt(ServerLevel serverLevel, DamageSource source, float amount) {\n\t\tsuper.actuallyHurt(serverLevel, source, amount);').replace('player.setItemInHand(hand, stack.getCraftingRemainingItem());', 'player.setItemInHand(hand, craftingRemainder(stack));').replace('ParticleTypes.INSTANT_EFFECT, 30)', 'SpellParticleOption.create(ParticleTypes.INSTANT_EFFECT, 0xFFFFFF, 1.0F), 30)')
    a=s.index('\t//// NBT ////'); b=s.index('\n\t//// SPAWN DATA ////', a)
    nbt='\t//// NBT ////\n\n\t@Override\n\tprotected void readAdditionalSaveData(final ValueInput input) {\n\t\tsuper.readAdditionalSaveData(input); readContainer(input); readVariant(input); this.setBaby(input.getBooleanOr(KEY_CHILD, false)); setupInventory(); this.getInventory().fromItemList(input.listOrEmpty("Inventory", ItemStack.CODEC)); CompoundTag behaviorTag = input.read("ExtraGolemsBehaviorData", CompoundTag.CODEC).orElseGet(CompoundTag::new); this.getContainer().ifPresent(container -> container.getBehaviors().forEach(bh -> bh.onReadData(this, behaviorTag)));\n\t}\n\n\t@Override\n\tprotected void addAdditionalSaveData(final ValueOutput output) {\n\t\tsuper.addAdditionalSaveData(output); writeContainer(output); writeVariant(output); output.putBoolean(KEY_CHILD, this.isBaby()); this.getInventory().storeAsItemList(output.list("Inventory", ItemStack.CODEC)); CompoundTag behaviorTag = new CompoundTag(); this.getContainer().ifPresent(container -> container.getBehaviors().forEach(bh -> bh.onWriteData(this, behaviorTag))); if (!behaviorTag.isEmpty()) output.store("ExtraGolemsBehaviorData", CompoundTag.CODEC, behaviorTag);\n\t}\n'
    s=s[:a]+nbt+s[b:]
    s=s.replace('this.inventory = new SimpleContainer(INVENTORY_SIZE);','this.inventory = new SimpleContainer(INVENTORY_SIZE) { @Override public void setChanged() { super.setChanged(); GolemBase.this.isInventoryChanged = true; } };').replace('\n\t\t\tsimplecontainer.removeListener(this);','').replace('\n\t\tthis.inventory.addListener(this);','').replace('public boolean wantsToPickUp(ItemStack stack)', 'public boolean wantsToPickUp(ServerLevel serverLevel, ItemStack stack)').replace('protected void dropEquipment() {\n\t\tsuper.dropEquipment();', 'protected void dropEquipment(ServerLevel serverLevel) {\n\t\tsuper.dropEquipment(serverLevel);').replace('protected void pickUpItem(ItemEntity item) {\n\t\tInventoryCarrier.pickUpItem(this, this, item);', 'protected void pickUpItem(ServerLevel serverLevel, ItemEntity item) {\n\t\tInventoryCarrier.pickUpItem(serverLevel, this, this, item);').replace('\n\t@Override\n\tpublic void containerChanged(Container container) {\n\t\tif (container == this.inventory) {\n\t\t\tthis.isInventoryChanged = true;\n\t\t}\n\t}\n','\n').replace('containerChanged(getInventory());','this.isInventoryChanged = true;')
    if 'private static ItemStack craftingRemainder' not in s: s=s.replace('\t//// MENU ////','\tprivate static ItemStack craftingRemainder(ItemStack stack) { final net.minecraft.world.item.ItemStackTemplate template = stack.getItem().getCraftingRemainder(); return template == null ? ItemStack.EMPTY : template.create(); }\n\n\t//// MENU ////')
    return s
edit('com/mcmoddev/golems/entity/GolemBase.java', patch_golem)

def patch_cmd(s):
    if 'import net.minecraft.server.permissions.Permissions;' not in s: s=s.replace('import net.minecraft.server.level.ServerLevel;','import net.minecraft.server.level.ServerLevel;\nimport net.minecraft.server.permissions.Permissions;')
    if 'import net.minecraft.world.level.storage.TagValueInput;' not in s: s=s.replace('import net.minecraft.world.phys.Vec3;','import net.minecraft.world.phys.Vec3;\nimport net.minecraft.world.level.storage.TagValueInput;\nimport net.minecraft.util.ProblemReporter;')
    return s.replace('.hasPermission(2)', '.permissions().hasPermission(Permissions.COMMANDS_GAMEMASTER)').replace('entity.load(tag);','entity.load(TagValueInput.create(ProblemReporter.DISCARDING, source.getLevel().registryAccess(), tag));').replace('entity.moveTo(pos.getX() + 0.5D, pos.getY(), pos.getZ() + 0.5D);','entity.snapTo(pos.getX() + 0.5D, pos.getY(), pos.getZ() + 0.5D);')
edit('com/mcmoddev/golems/network/SummonGolemCommand.java', patch_cmd)

def patch_packet(s):
    if 'import net.minecraft.server.permissions.Permissions;' not in s: s=s.replace('import net.minecraft.server.level.ServerPlayer;','import net.minecraft.server.level.ServerPlayer;\nimport net.minecraft.server.permissions.Permissions;\nimport net.minecraft.server.permissions.Permission;')
    s=s.replace('if (!player.hasPermissions(ExtraGolems.CONFIG.debugPermissionLevel())) {','if (ExtraGolems.CONFIG.debugPermissionLevel() > 0 && !player.permissions().hasPermission(permissionForLevel(ExtraGolems.CONFIG.debugPermissionLevel()))) {').replace('player.displayClientMessage(', 'player.sendSystemMessage(').replace('), false);', '));')
    if 'permissionForLevel(' not in s.split('public static void handle')[0]:
        idx=s.rfind('\n}'); helper='\n    private static Permission permissionForLevel(int level) {\n        if (level >= 4) return Permissions.COMMANDS_OWNER;\n        if (level >= 3) return Permissions.COMMANDS_ADMIN;\n        if (level >= 2) return Permissions.COMMANDS_GAMEMASTER;\n        return Permissions.COMMANDS_MODERATOR;\n    }\n'; s=s[:idx]+helper+s[idx:]
    return s
edit('com/mcmoddev/golems/network/ServerBoundSpawnGolemPacket.java', patch_packet)

print('Applied NeoForge/Minecraft 26.1.2 pass 2 common/gameplay migration.')
