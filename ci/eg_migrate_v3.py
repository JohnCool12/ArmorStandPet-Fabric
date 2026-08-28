#!/usr/bin/env python3
from pathlib import Path
import re, shutil, sys
ROOT=Path(sys.argv[1] if len(sys.argv)>1 else 'work').resolve(); SRC=ROOT/'src/main/java'

def edit(rel, fn):
 p=SRC/rel
 if not p.exists(): return
 s=p.read_text(); n=fn(s)
 if n!=s: p.write_text(n)

def rep(rel, pairs):
 edit(rel, lambda s: __import__('functools').reduce(lambda x,p:x.replace(*p), pairs, s))

client=SRC/'com/mcmoddev/golems/client'
shutil.rmtree(client, ignore_errors=True)
(client/'entity').mkdir(parents=True, exist_ok=True)
(client/'EGClientEvents.java').write_text(r'''package com.mcmoddev.golems.client;
import com.mcmoddev.golems.EGRegistry;
import com.mcmoddev.golems.client.entity.GolemRenderer;
import net.minecraft.client.renderer.entity.EntityRenderers;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.event.lifecycle.FMLClientSetupEvent;
public final class EGClientEvents {
 private EGClientEvents() {}
 public static void register(IEventBus bus) { bus.addListener(EGClientEvents::clientSetup); }
 private static void clientSetup(FMLClientSetupEvent event) { event.enqueueWork(() -> EntityRenderers.register(EGRegistry.EntityReg.GOLEM.get(), GolemRenderer::new)); }
}
''')
(client/'entity/GolemRenderer.java').write_text(r'''package com.mcmoddev.golems.client.entity;
import com.mcmoddev.golems.entity.GolemBase;
import net.minecraft.client.model.animal.golem.IronGolemModel;
import net.minecraft.client.model.geom.ModelLayers;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.client.renderer.entity.state.IronGolemRenderState;
import net.minecraft.resources.Identifier;
public final class GolemRenderer extends MobRenderer<GolemBase, IronGolemRenderState, IronGolemModel> {
 private static final Identifier TEXTURE = Identifier.withDefaultNamespace("textures/entity/iron_golem/iron_golem.png");
 public GolemRenderer(EntityRendererProvider.Context context) { super(context, new IronGolemModel(context.bakeLayer(ModelLayers.IRON_GOLEM)), 0.7F); }
 @Override public Identifier getTextureLocation(IronGolemRenderState state) { return TEXTURE; }
 @Override public IronGolemRenderState createRenderState() { return new IronGolemRenderState(); }
 @Override public void extractRenderState(GolemBase entity, IronGolemRenderState state, float partialTick) {
  super.extractRenderState(entity, state, partialTick);
  state.attackTicksRemaining = entity.getAttackAnimationTick() > 0 ? entity.getAttackAnimationTick() - partialTick : 0.0F;
  state.offerFlowerTick = entity.getOfferFlowerTick();
  state.crackiness = entity.getCrackiness();
 }
}
''')

edit('com/mcmoddev/golems/item/GuideBookItem.java', lambda s: re.sub(r'\s*if \(playerIn\.getCommandSenderWorld\(\)\.isClientSide\(\)\) \{.*?\n\s*\}', '', s, flags=re.S).replace('import com.mcmoddev.golems.client.EGClientEvents;\n',''))
edit('com/mcmoddev/golems/entity/IExtraGolem.java', lambda s: s.replace('import net.minecraft.world.inventory.ContainerListener;\n','').replace('IInventoryProvider, ContainerListener, RangedAttackMob', 'IInventoryProvider, RangedAttackMob'))

for p in SRC.rglob('*.java'):
 s=p.read_text()
 s=re.sub(r'\b(\w+)\.isClientSide\b(?!\s*\()', r'\1.isClientSide()', s)
 s=s.replace('IntProvider.NON_NEGATIVE_CODEC','IntProviders.NON_NEGATIVE_CODEC').replace('IntProvider.POSITIVE_CODEC','IntProviders.POSITIVE_CODEC').replace('IntProvider.codec(','IntProviders.codec(')
 s=s.replace('.getMinValue()', '.minInclusive()').replace('.getMaxValue()', '.maxInclusive()').replace('.getType()', '.codec()')
 s=s.replace('getCraftingRemainingItem()', 'getCraftingRemainder()').replace('TagParser.parseTag(', 'TagParser.parseCompoundFully(')
 if 'IntProviders.' in s and 'net.minecraft.util.valueproviders.IntProviders' not in s:
  if 'import net.minecraft.util.valueproviders.IntProvider;\n' in s:
   s=s.replace('import net.minecraft.util.valueproviders.IntProvider;\n','import net.minecraft.util.valueproviders.IntProvider;\nimport net.minecraft.util.valueproviders.IntProviders;\n')
  else:
   i=s.find('\n', s.find('package ')); s=s[:i+1]+'\nimport net.minecraft.util.valueproviders.IntProviders;\n'+s[i+1:]
 p.write_text(s)

rep('com/mcmoddev/golems/block/UtilityBlock.java', [('net.minecraft.world.ticks.ScheduledTickAccess','net.minecraft.world.level.ScheduledTickAccess')])
rep('com/mcmoddev/golems/data/behavior/util/GolemPredicate.java', [('(e.asMob().isInWaterOrBubble() || e.asMob().isInRain())','e.asMob().isInWater()'),('!e.asMob().isInWaterOrBubble()','!e.asMob().isInWater()'),('!golem.level().isDay()', 'golem.level().getSkyDarken() >= 4')])
rep('com/mcmoddev/golems/entity/goal/SwimUpGoal.java', [('!golem.level().isDay()', 'golem.level().getSkyDarken() >= 4')])

def patch_golem(s):
 s=re.sub(r'\n\s*@Override\s+public void dataChanged\(net\.minecraft\.world\.inventory\.AbstractContainerMenu menu, int dataSlotIndex, int value\) \{.*?\n\s*\}', '', s, flags=re.S)
 s=s.replace('return this.isSunBurnTick();','return this.level().getSkyDarken() < 4 && this.level().canSeeSky(this.blockPosition());')
 s=re.sub(r'@Override\s+public boolean canAttackType\(final EntityType<\?> type\) \{.*?return super\.canAttackType\(type\);\s*\}', '@Override\n\tpublic boolean canAttack(final LivingEntity target) {\n\t\tfinal EntityType<?> type = target.getType();\n\t\tif (type == EntityType.PLAYER && this.isPlayerCreated() && !ExtraGolems.CONFIG.enableFriendlyFire()) return false;\n\t\tif (type == EntityType.VILLAGER || type == EGRegistry.EntityReg.GOLEM.get() || type == EntityType.IRON_GOLEM || type == EntityType.SNOW_GOLEM) return false;\n\t\treturn super.canAttack(target);\n\t}', s, flags=re.S)
 s=s.replace('@Override\n\tpublic ItemStack getPickedResult(final HitResult ray)', 'public ItemStack getPickedResult(final HitResult ray)')
 s=re.sub(r'@Override\s+protected ResourceKey<net\.minecraft\.world\.level\.storage\.loot\.LootTable> getDefaultLootTable\(\) \{.*?\n\s*\}', '@Override\n\tpublic Optional<ResourceKey<net.minecraft.world.level.storage.loot.LootTable>> getLootTable() {\n\t\tfinal Optional<GolemContainer> oContainer = getContainer();\n\t\tif (oContainer.isEmpty()) return super.getLootTable();\n\t\treturn Optional.of(ResourceKey.create(net.minecraft.core.registries.Registries.LOOT_TABLE, oContainer.get().getLootTable()));\n\t}', s, flags=re.S)
 s=s.replace('public void customServerAiStep() {\n\t\tsuper.customServerAiStep();', 'public void customServerAiStep(ServerLevel serverLevel) {\n\t\tsuper.customServerAiStep(serverLevel);')
 s=s.replace('this.isInWaterRainOrBubble()', 'this.isInWater()')
 s=s.replace('this.level().getBiome(this.blockPosition()).is(BiomeTags.SNOW_GOLEM_MELTS)', 'serverLevel.environmentAttributes().getValue(net.minecraft.world.attribute.EnvironmentAttributes.SNOW_GOLEM_MELTS, this.position())')
 s=s.replace('public boolean isInvulnerableTo(DamageSource pSource)', 'public boolean isInvulnerableTo(ServerLevel serverLevel, DamageSource pSource)').replace('super.isInvulnerableTo(pSource)', 'super.isInvulnerableTo(serverLevel, pSource)')
 s=s.replace('public boolean causeFallDamage(float distance, float damageMultiplier, DamageSource source)', 'public boolean causeFallDamage(double distance, float damageMultiplier, DamageSource source)')
 s=s.replace('public boolean doHurtTarget(Entity target)', 'public boolean doHurtTarget(ServerLevel serverLevel, Entity target)').replace('super.doHurtTarget(target)', 'super.doHurtTarget(serverLevel, target)')
 s=s.replace('protected void actuallyHurt(DamageSource source, float amount)', 'protected void actuallyHurt(ServerLevel serverLevel, DamageSource source, float amount)').replace('super.actuallyHurt(source, amount)', 'super.actuallyHurt(serverLevel, source, amount)')
 s=s.replace('ParticleTypes.INSTANT_EFFECT, 30', 'ParticleTypes.HAPPY_VILLAGER, 30')
 s=re.sub(r'@Override\s+public void readAdditionalSaveData\(final CompoundTag tag\) \{.*?\n\s*public void writeInventory\(CompoundTag tag, net\.minecraft\.core\.HolderLookup\.Provider registries\) \{.*?\n\s*\}', '@Override\n\tprotected void readAdditionalSaveData(final net.minecraft.world.level.storage.ValueInput input) {\n\t\tsuper.readAdditionalSaveData(input);\n\t\tCompoundTag tag = input.read("ExtraGolemsData", CompoundTag.CODEC).orElseGet(CompoundTag::new);\n\t\treadContainer(tag); readVariant(tag); this.setBaby(tag.getBooleanOr(KEY_CHILD, false));\n\t\tsetupInventory(); this.readInventoryFromTag(input);\n\t\tthis.getContainer().ifPresent(container -> container.getBehaviors().forEach(b -> b.onReadData(this, tag)));\n\t}\n', s, flags=re.S)
 s=re.sub(r'@Override\s+public void addAdditionalSaveData\(final CompoundTag tag\) \{.*?\n\s*\}', '@Override\n\tprotected void addAdditionalSaveData(final net.minecraft.world.level.storage.ValueOutput output) {\n\t\tsuper.addAdditionalSaveData(output);\n\t\tCompoundTag tag = new CompoundTag(); writeContainer(tag); writeVariant(tag); tag.putBoolean(KEY_CHILD, this.isBaby());\n\t\tthis.getContainer().ifPresent(container -> container.getBehaviors().forEach(b -> b.onWriteData(this, tag)));\n\t\toutput.store("ExtraGolemsData", CompoundTag.CODEC, tag); this.writeInventoryToTag(output);\n\t}', s, flags=re.S)
 s=re.sub(r'\s*simplecontainer\.removeListener\(this\);', '', s); s=re.sub(r'\s*this\.inventory\.addListener\(this\);', '', s)
 s=s.replace('public boolean wantsToPickUp(ItemStack stack)', 'public boolean wantsToPickUp(ServerLevel serverLevel, ItemStack stack)')
 s=s.replace('protected void dropEquipment() {\n\t\tsuper.dropEquipment();', 'protected void dropEquipment(ServerLevel serverLevel) {\n\t\tsuper.dropEquipment(serverLevel);')
 s=s.replace('protected void pickUpItem(ItemEntity item) {\n\t\tInventoryCarrier.pickUpItem(this, this, item);', 'protected void pickUpItem(ServerLevel serverLevel, ItemEntity item) {\n\t\tInventoryCarrier.pickUpItem(serverLevel, this, this, item);')
 s=s.replace('containerChanged(getInventory());', 'this.isInventoryChanged = true;').replace('@Override\n\tpublic void containerChanged(Container container)', 'public void containerChanged(Container container)')
 return s
edit('com/mcmoddev/golems/entity/GolemBase.java', patch_golem)

def spawnitem(s):
 s=s.replace('entity.moveTo(spawnPos.getX(), spawnPos.getY(), spawnPos.getZ());','entity.snapTo(spawnPos.getX()+0.5D, spawnPos.getY(), spawnPos.getZ()+0.5D, 0.0F, 0.0F);')
 s=s.replace('level.addFreshEntity(entity);\n\t\t\tentity.finalizeSpawn((ServerLevel) level, level.getCurrentDifficultyAt(spawnPos), EntitySpawnReason.SPAWN_EGG, null);', 'ServerLevel serverLevel = (ServerLevel) level;\n\t\t\tserverLevel.addFreshEntity(entity);\n\t\t\tentity.finalizeSpawn(serverLevel, serverLevel.getCurrentDifficultyAt(spawnPos), EntitySpawnReason.SPAWN_ITEM_USE, null);')
 s=s.replace('world.random', 'world.getRandom()')
 s=re.sub(r'\n\s*@Override\s+public void appendHoverText\(.*?\n\s*\}', '', s, flags=re.S)
 return s
edit('com/mcmoddev/golems/item/SpawnGolemItem.java', spawnitem)
rep('com/mcmoddev/golems/item/GolemSpellItem.java', [('this.getDescriptionId(stack)','this.getDescriptionId()')])
rep('com/mcmoddev/golems/data/behavior/util/TargetedMobEffects.java', [('mob.level().getNearbyEntities(', '((ServerLevel) mob.level()).getNearbyEntities('),('rolls.getType()', 'rolls.codec()'), ('that.rolls.getType()', 'that.rolls.codec()')])
rep('com/mcmoddev/golems/data/behavior/SetFireBehavior.java', [('self.level().getNearbyEntities(', '((ServerLevel) self.level()).getNearbyEntities(')])
edit('com/mcmoddev/golems/data/behavior/TemptBehavior.java', lambda s: re.sub(r'Ingredient ingredient = holderSet\.unwrap\(\)\.map\(.*?\);', 'Ingredient ingredient = Ingredient.of(holderSet);', s))
for rel in ['com/mcmoddev/golems/data/behavior/data/UseFuelBehaviorData.java','com/mcmoddev/golems/data/behavior/data/ExplodeBehaviorData.java','com/mcmoddev/golems/data/behavior/AbstractShootBehavior.java']:
 edit(rel, lambda s: s.replace('tag.getInt(KEY_FUEL)','tag.getIntOr(KEY_FUEL, 0)').replace('tag.getInt(KEY_FUSE)','tag.getIntOr(KEY_FUSE, 0)').replace('tag.getBoolean(KEY_FUSE_LIT)','tag.getBooleanOr(KEY_FUSE_LIT, false)').replace('tag.getInt(KEY_AMMO)','tag.getIntOr(KEY_AMMO, 0)'))
for rel in ['com/mcmoddev/golems/data/behavior/UseFuelBehavior.java','com/mcmoddev/golems/data/behavior/ExplodeBehavior.java']:
 edit(rel, lambda s: s.replace('tag.getCompound(KEY_FUEL_HELPER)', 'tag.getCompoundOrEmpty(KEY_FUEL_HELPER)').replace('tag.getCompound(KEY_EXPLODE_HELPER)', 'tag.getCompoundOrEmpty(KEY_EXPLODE_HELPER)'))
edit('com/mcmoddev/golems/data/behavior/UseFuelBehavior.java', lambda s: s.replace('stack.getBurnTime(RecipeType.SMELTING)', 'stack.getBurnTime(RecipeType.SMELTING, ((ServerLevel) player.level()).fuelValues())'))
rep('com/mcmoddev/golems/data/behavior/ShootSnowballsBehavior.java', [('new Snowball(mob.level(), mob)', 'new Snowball((ServerLevel) mob.level(), mob, new ItemStack(Items.SNOWBALL))')])

def summon(s):
 s=s.replace('EntityType.create(tag, self.level()).ifPresent(e -> {', 'Entity e = this.entity.create(level, EntitySpawnReason.MOB_SUMMONED);\n\t\t\tif (e != null) {')
 s=s.replace('\t\t\t});\n\t\t}\n\t\treturn amount > 0;', '\t\t\t}\n\t\t}\n\t\treturn amount > 0;')
 s=s.replace('mob.setPersistentAngerTarget(target.getUUID());\n\t\t\t\t\tmob.startPersistentAngerTimer();', 'mob.startPersistentAngerTimer();')
 return s
edit('com/mcmoddev/golems/data/behavior/SummonBehavior.java', summon)
for rel in ['com/mcmoddev/golems/data/behavior/SplitBehavior.java','com/mcmoddev/golems/block/GolemHeadBlock.java']:
 edit(rel, lambda s: s.replace('mob.level().getCurrentDifficultyAt(', '((ServerLevel) mob.level()).getCurrentDifficultyAt(').replace('level.getCurrentDifficultyAt(', '((ServerLevel) level).getCurrentDifficultyAt('))

def head(s):
 s=s.replace('EntityType.SNOW_GOLEM.create(level)', 'EntityType.SNOW_GOLEM.create(level, EntitySpawnReason.MOB_SUMMONED)').replace('EntityType.IRON_GOLEM.create(level)', 'EntityType.IRON_GOLEM.create(level, EntitySpawnReason.MOB_SUMMONED)')
 s=re.sub(r'(entitysnowman|ironGolem|golem)\.moveTo\(([^;]+)\);', r'\1.snapTo(\2);', s)
 return s
edit('com/mcmoddev/golems/block/GolemHeadBlock.java', head)
rep('com/mcmoddev/golems/util/DeferredBlockState.java', [('BuiltInRegistries.BLOCK.get(this.block)','BuiltInRegistries.BLOCK.getValue(this.block)')])
rep('com/mcmoddev/golems/EGEvents.java', [('registry.getOrCreateTag(VILLAGER_SUMMONABLE)','registry.get(VILLAGER_SUMMONABLE).orElseThrow()')])
rep('com/mcmoddev/golems/entity/goal/MoveToItemGoal.java', [('entity.wantsToPickUp(e.getItem())','entity.wantsToPickUp((ServerLevel) entity.level(), e.getItem())')])
rep('com/mcmoddev/golems/entity/goal/InertGoal.java', [('neutralMob.setRemainingPersistentAngerTime(0)','neutralMob.setPersistentAngerEndTime(0L); neutralMob.setPersistentAngerTarget(null)')])
edit('com/mcmoddev/golems/data/behavior/WearBannerBehavior.java', lambda s: s.replace('mob.spawnAtLocation(banner, mob.getBbHeight() * 0.9F)', 'mob.spawnAtLocation((ServerLevel) mob.level(), banner, mob.getBbHeight() * 0.9F)'))

def cmd(s):
 s=s.replace('.requires(p -> p.hasPermission(2))', '.requires(p -> p.permissions().hasPermission(net.minecraft.server.permissions.Permissions.COMMANDS_GAMEMASTER))').replace('entity.load(tag);','').replace('entity.moveTo(pos.getX() + 0.5D, pos.getY(), pos.getZ() + 0.5D);','entity.snapTo(pos.getX() + 0.5D, pos.getY(), pos.getZ() + 0.5D, 0.0F, 0.0F);')
 return s
edit('com/mcmoddev/golems/network/SummonGolemCommand.java', cmd)
edit('com/mcmoddev/golems/network/ServerBoundSpawnGolemPacket.java', lambda s: s.replace('player.hasPermissions(ExtraGolems.CONFIG.debugPermissionLevel())','player.permissions().hasPermission(net.minecraft.server.permissions.Permissions.COMMANDS_GAMEMASTER)').replace('player.displayClientMessage(', 'player.sendSystemMessage(').replace(', false);', ');'))
print('Applied deterministic 26.1.2 migration pass 3')
