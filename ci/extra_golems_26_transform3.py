from pathlib import Path
import re

ROOT = Path('project/src/main/java')

# IExtraGolem: ContainerListener no longer represents inventory-dirty callbacks in 26.1.
p = ROOT / 'com/mcmoddev/golems/entity/IExtraGolem.java'
s = p.read_text()
s = s.replace('import net.minecraft.nbt.CompoundTag;\n', 'import net.minecraft.nbt.ValueInput;\nimport net.minecraft.nbt.ValueOutput;\n')
s = s.replace('import net.minecraft.world.inventory.ContainerListener;\n', '')
s = s.replace('IInventoryProvider, ContainerListener, RangedAttackMob', 'IInventoryProvider, RangedAttackMob')
s = s.replace('default void writeContainer(CompoundTag pCompound) {\n\t\tgetGolemId().ifPresent(id -> pCompound.putString(KEY_GOLEM_ID, id.toString()));\n\t}',
'''default void writeContainer(ValueOutput output) {\n\t\tgetGolemId().ifPresent(id -> output.putString(KEY_GOLEM_ID, id.toString()));\n\t}''')
s = re.sub(r'default void readContainer\(CompoundTag pCompound\) \{.*?\n\t\}', '''default void readContainer(ValueInput input) {\n\t\tfinal String id = input.getStringOr(KEY_GOLEM_ID, "");\n\t\tif (!id.isEmpty()) {\n\t\t\tsetGolemId(Identifier.parse(id));\n\t\t}\n\t\tfinal String legacy = input.getStringOr("Material", "");\n\t\tif (!legacy.isEmpty()) {\n\t\t\tsetGolemId(Identifier.parse(legacy));\n\t\t}\n\t}''', s, count=1, flags=re.S)
p.write_text(s)

# IVariantProvider: ValueInput/ValueOutput persistence.
p = ROOT / 'com/mcmoddev/golems/entity/IVariantProvider.java'
s = p.read_text()
s = s.replace('import net.minecraft.nbt.CompoundTag;\n', 'import net.minecraft.nbt.ValueInput;\nimport net.minecraft.nbt.ValueOutput;\n')
s = re.sub(r'default void writeVariant\(final CompoundTag tag\) \{.*?\n\t\}', '''default void writeVariant(final ValueOutput output) {\n\t\toutput.putByte(KEY_VARIANT, (byte) getVariant());\n\t}''', s, count=1, flags=re.S)
s = re.sub(r'default void readVariant\(final CompoundTag tag\) \{.*?\n\t\}', '''default void readVariant(final ValueInput input) {\n\t\tsetVariant(input.getByteOr(KEY_VARIANT, (byte) 0));\n\t}''', s, count=1, flags=re.S)
p.write_text(s)

# Behavior persistence hooks now receive the entity save IO views directly.
p = ROOT / 'com/mcmoddev/golems/data/behavior/Behavior.java'
s = p.read_text()
s = s.replace('import net.minecraft.nbt.CompoundTag;\n', 'import net.minecraft.nbt.ValueInput;\nimport net.minecraft.nbt.ValueOutput;\n')
s = s.replace('public void onWriteData(final IExtraGolem entity, final CompoundTag tag)', 'public void onWriteData(final IExtraGolem entity, final ValueOutput output)')
s = s.replace('public void onReadData(final IExtraGolem entity, final CompoundTag tag)', 'public void onReadData(final IExtraGolem entity, final ValueInput input)')
p.write_text(s)

# Behavior runtime-data persistence no longer needs temporary CompoundTags.
p = ROOT / 'com/mcmoddev/golems/data/behavior/data/IBehaviorData.java'
p.write_text('''package com.mcmoddev.golems.data.behavior.data;\n\nimport net.minecraft.nbt.ValueInput;\nimport net.minecraft.nbt.ValueOutput;\n\n/** Runtime data owned by one attached golem behavior. */\npublic interface IBehaviorData {\n    void writeData(ValueOutput output);\n    void readData(ValueInput input);\n}\n''')

p = ROOT / 'com/mcmoddev/golems/data/behavior/data/ExplodeBehaviorData.java'
s = p.read_text()
s = s.replace('import net.minecraft.nbt.CompoundTag;\n', 'import net.minecraft.nbt.ValueInput;\nimport net.minecraft.nbt.ValueOutput;\n')
s = re.sub(r'@Override\n\tpublic CompoundTag serializeNBT\([^)]*\) \{.*?\n\t\}\n\n\t@Override\n\tpublic void deserializeNBT\([^)]*CompoundTag tag\) \{.*?\n\t\}', '''@Override\n\tpublic void writeData(ValueOutput output) {\n\t\toutput.putInt(KEY_FUSE, fuse);\n\t\toutput.putBoolean(KEY_FUSE_LIT, fuseLit);\n\t}\n\n\t@Override\n\tpublic void readData(ValueInput input) {\n\t\tthis.fuse = input.getIntOr(KEY_FUSE, 0);\n\t\tthis.fuseLit = input.getBooleanOr(KEY_FUSE_LIT, false);\n\t}''', s, count=1, flags=re.S)
p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/data/behavior/data/UseFuelBehaviorData.java'
s = p.read_text()
s = s.replace('import net.minecraft.nbt.CompoundTag;\n', 'import net.minecraft.nbt.ValueInput;\nimport net.minecraft.nbt.ValueOutput;\n')
s = re.sub(r'@Override\n\tpublic CompoundTag serializeNBT\([^)]*\) \{.*?\n\t\}\n\n\t@Override\n\tpublic void deserializeNBT\([^)]*CompoundTag tag\) \{.*?\n\t\}', '''@Override\n\tpublic void writeData(ValueOutput output) {\n\t\toutput.putInt(KEY_FUEL, entity.getFuel());\n\t}\n\n\t@Override\n\tpublic void readData(ValueInput input) {\n\t\tentity.setFuel(input.getIntOr(KEY_FUEL, 0));\n\t}''', s, count=1, flags=re.S)
p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/data/behavior/data/ShootBehaviorData.java'
s = p.read_text()
s = s.replace('import net.minecraft.nbt.CompoundTag;\n', 'import net.minecraft.nbt.ValueInput;\nimport net.minecraft.nbt.ValueOutput;\n')
s = re.sub(r'@Override\n\tpublic CompoundTag serializeNBT\([^)]*\) \{.*?\n\t\}\n\n\t@Override\n\tpublic void deserializeNBT\([^)]*CompoundTag tag\) \{.*?\n\t\}', '''@Override\n\tpublic void writeData(ValueOutput output) {\n\t\t// no additional data\n\t}\n\n\t@Override\n\tpublic void readData(ValueInput input) {\n\t\t// no additional data\n\t}''', s, count=1, flags=re.S)
p.write_text(s)

# Nested behavior data keeps the exact legacy key layout, now through child IO views.
p = ROOT / 'com/mcmoddev/golems/data/behavior/ExplodeBehavior.java'
s = p.read_text()
s = s.replace('import net.minecraft.nbt.CompoundTag;\n', 'import net.minecraft.nbt.ValueInput;\nimport net.minecraft.nbt.ValueOutput;\n')
s = re.sub(r'@Override\n\tpublic void onWriteData\(final IExtraGolem entity, final CompoundTag tag\) \{.*?\n\t\}\n\n\t@Override\n\tpublic void onReadData\(final IExtraGolem entity, final CompoundTag tag\) \{.*?\n\t\}', '''@Override\n\tpublic void onWriteData(final IExtraGolem entity, final ValueOutput output) {\n\t\tentity.getBehaviorData(ExplodeBehaviorData.class).ifPresent(data -> data.writeData(output.child(KEY_EXPLOSION_HELPER)));\n\t}\n\n\t@Override\n\tpublic void onReadData(final IExtraGolem entity, final ValueInput input) {\n\t\tentity.getBehaviorData(ExplodeBehaviorData.class).ifPresent(data -> data.readData(input.childOrEmpty(KEY_EXPLOSION_HELPER)));\n\t}''', s, count=1, flags=re.S)
p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/data/behavior/UseFuelBehavior.java'
s = p.read_text()
s = s.replace('import net.minecraft.nbt.CompoundTag;\n', 'import net.minecraft.nbt.ValueInput;\nimport net.minecraft.nbt.ValueOutput;\n')
s = s.replace('public void onWriteData(final IExtraGolem entity, final CompoundTag tag) {\n\t\tentity.getBehaviorData(UseFuelBehaviorData.class).ifPresent(helper -> tag.put(KEY_FUEL_HELPER, helper.serializeNBT(((net.minecraft.world.entity.Entity)entity).level().registryAccess())));\n\t}',
'''public void onWriteData(final IExtraGolem entity, final ValueOutput output) {\n\t\tentity.getBehaviorData(UseFuelBehaviorData.class).ifPresent(helper -> helper.writeData(output.child(KEY_FUEL_HELPER)));\n\t}''')
s = s.replace('public void onReadData(final IExtraGolem entity, final CompoundTag tag) {\n\t\tentity.getBehaviorData(UseFuelBehaviorData.class).ifPresent(helper -> helper.deserializeNBT(((net.minecraft.world.entity.Entity)entity).level().registryAccess(), tag.getCompoundOrEmpty(KEY_FUEL_HELPER)));\n\t}',
'''public void onReadData(final IExtraGolem entity, final ValueInput input) {\n\t\tentity.getBehaviorData(UseFuelBehaviorData.class).ifPresent(helper -> helper.readData(input.childOrEmpty(KEY_FUEL_HELPER)));\n\t}''')
s = s.replace('stack.getCraftingRemainingItem()', 'stack.getCraftingRemainder()')
p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/data/behavior/AbstractShootBehavior.java'
s = p.read_text()
s = s.replace('import net.minecraft.nbt.CompoundTag;\n', 'import net.minecraft.nbt.ValueInput;\nimport net.minecraft.nbt.ValueOutput;\n')
s = s.replace('public void onWriteData(final IExtraGolem entity, final CompoundTag tag)', 'public void onWriteData(final IExtraGolem entity, final ValueOutput output)')
s = s.replace('tag.putInt(KEY_AMMO, entity.getAmmo());', 'output.putInt(KEY_AMMO, entity.getAmmo());')
s = s.replace('public void onReadData(final IExtraGolem entity, final CompoundTag tag)', 'public void onReadData(final IExtraGolem entity, final ValueInput input)')
s = s.replace('entity.setAmmo(tag.getIntOr(KEY_AMMO, 0));', 'entity.setAmmo(input.getIntOr(KEY_AMMO, 0));')
p.write_text(s)

# GolemBase structural 26.1 migration.
p = ROOT / 'com/mcmoddev/golems/entity/GolemBase.java'
s = p.read_text()
s = s.replace('import net.minecraft.nbt.CompoundTag;\n', 'import net.minecraft.nbt.ValueInput;\nimport net.minecraft.nbt.ValueOutput;\n')
s = s.replace('import net.minecraft.core.particles.ParticleTypes;\n', 'import net.minecraft.core.particles.ParticleTypes;\nimport net.minecraft.core.particles.SpellParticleOption;\n')
s = s.replace('import net.minecraft.world.Container;\n', '')
s = s.replace('import net.minecraft.world.phys.HitResult;\n', '')

# canAttackType was removed; preserve the old type policy through canAttack(LivingEntity).
s = re.sub(r'\n\t@Override\n\tpublic boolean canAttackType\(final EntityType<\?> type\) \{.*?\n\t\}\n', '''\n\t@Override\n\tpublic boolean canAttack(final LivingEntity target) {\n\t\tfinal EntityType<?> type = target.getType();\n\t\tif (type == EntityType.PLAYER && this.isPlayerCreated()) {\n\t\t\treturn ExtraGolems.CONFIG.enableFriendlyFire() && super.canAttack(target);\n\t\t}\n\t\tif (type == EntityType.VILLAGER || type == EGRegistry.EntityReg.GOLEM.get() || type == EntityType.IRON_GOLEM\n\t\t\t\t|| type == EntityType.SNOW_GOLEM) {\n\t\t\treturn false;\n\t\t}\n\t\treturn super.canAttack(target);\n\t}\n''', s, count=1, flags=re.S)

# Pick-block hook changed to no-arg getPickResult.
s = s.replace('public ItemStack getPickedResult(final HitResult ray)', 'public ItemStack getPickResult()')

# Custom loot now belongs in dropFromLootTable because getLootTable is final.
s = re.sub(r'\n\t@Override\n\tprotected ResourceKey<net\.minecraft\.world\.level\.storage\.loot\.LootTable> getDefaultLootTable\(\) \{.*?\n\t\}\n', '''\n\t@Override\n\tprotected void dropFromLootTable(final ServerLevel serverLevel, final DamageSource source, final boolean playerKilled) {\n\t\tfinal Optional<GolemContainer> oContainer = getContainer();\n\t\tif (oContainer.isEmpty()) {\n\t\t\tsuper.dropFromLootTable(serverLevel, source, playerKilled);\n\t\t\treturn;\n\t\t}\n\t\tfinal ResourceKey<net.minecraft.world.level.storage.loot.LootTable> key = ResourceKey.create(\n\t\t\t\tnet.minecraft.core.registries.Registries.LOOT_TABLE, oContainer.get().getLootTable());\n\t\tthis.dropFromLootTable(serverLevel, source, playerKilled, key);\n\t}\n''', s, count=1, flags=re.S)

s = s.replace('public void customServerAiStep() {\n\t\tsuper.customServerAiStep();',
              'protected void customServerAiStep(final ServerLevel serverLevel) {\n\t\tsuper.customServerAiStep(serverLevel);')
s = s.replace('this.hurt(this.damageSources().drown(), 1.0F);', 'this.hurtServer(serverLevel, this.damageSources().drown(), 1.0F);')
s = s.replace('this.hurt(this.damageSources().onFire(), 1.0F);', 'this.hurtServer(serverLevel, this.damageSources().onFire(), 1.0F);')

s = s.replace('public boolean isInvulnerableTo(DamageSource pSource) {\n\t\tif (super.isInvulnerableTo(pSource)) {',
              'public boolean isInvulnerableTo(final ServerLevel serverLevel, final DamageSource pSource) {\n\t\tif (super.isInvulnerableTo(serverLevel, pSource)) {')
s = s.replace('public boolean causeFallDamage(float distance, float damageMultiplier, DamageSource source)',
              'public boolean causeFallDamage(double distance, float damageMultiplier, DamageSource source)')
s = s.replace('this.hurt(this.damageSources().fall(), (float) i);',
              'if (this.level() instanceof ServerLevel serverLevel) {\n\t\t\t\t\tthis.hurtServer(serverLevel, this.damageSources().fall(), (float) i);\n\t\t\t\t}')

s = s.replace('public boolean doHurtTarget(Entity target) {\n\t\tif (super.doHurtTarget(target)) {',
              'public boolean doHurtTarget(final ServerLevel serverLevel, final Entity target) {\n\t\tif (super.doHurtTarget(serverLevel, target)) {')
s = s.replace('protected void actuallyHurt(DamageSource source, float amount) {\n\t\tsuper.actuallyHurt(source, amount);',
              'protected void actuallyHurt(final ServerLevel serverLevel, final DamageSource source, final float amount) {\n\t\tsuper.actuallyHurt(serverLevel, source, amount);')

s = s.replace('stack.getCraftingRemainingItem()', 'stack.getCraftingRemainder()')
s = s.replace('ParticleTypes.INSTANT_EFFECT, 30);',
              'SpellParticleOption.create(ParticleTypes.INSTANT_EFFECT, 0xFFFFFF, 1.0F), 30);')

# Entity save/load and inventory item-list codec.
s = re.sub(r'\n\t@Override\n\tpublic void readAdditionalSaveData\(final CompoundTag tag\) \{.*?\n\t@Override\n\tpublic void addAdditionalSaveData\(final CompoundTag tag\) \{.*?\n\t\}\n', '''\n\t@Override\n\tprotected void readAdditionalSaveData(final ValueInput input) {\n\t\tsuper.readAdditionalSaveData(input);\n\t\treadContainer(input);\n\t\treadVariant(input);\n\t\tthis.setBaby(input.getBooleanOr(KEY_CHILD, false));\n\t\tsetupInventory();\n\t\tthis.inventory.fromItemList(input.listOrEmpty("Inventory", ItemStack.CODEC));\n\t\tthis.getContainer().ifPresent(container -> container.getBehaviors().forEach(b -> b.onReadData(this, input)));\n\t}\n\n\t@Override\n\tprotected void addAdditionalSaveData(final ValueOutput output) {\n\t\tsuper.addAdditionalSaveData(output);\n\t\twriteContainer(output);\n\t\twriteVariant(output);\n\t\toutput.putBoolean(KEY_CHILD, this.isBaby());\n\t\tthis.inventory.storeAsItemList(output.list("Inventory", ItemStack.CODEC));\n\t\tthis.getContainer().ifPresent(container -> container.getBehaviors().forEach(b -> b.onWriteData(this, output)));\n\t}\n''', s, count=1, flags=re.S)

# Listener-based SimpleContainer dirty tracking was removed. Override setChanged instead.
s = re.sub(r'\t@Override\n\tpublic void setupInventory\(\) \{.*?\n\t\}\n\n\t@Override\n\tpublic boolean wantsToPickUp\(ItemStack stack\)', '''\t@Override\n\tpublic void setupInventory() {\n\t\tfinal SimpleContainer old = this.inventory;\n\t\tthis.inventory = new SimpleContainer(INVENTORY_SIZE) {\n\t\t\t@Override\n\t\t\tpublic void setChanged() {\n\t\t\t\tsuper.setChanged();\n\t\t\t\tGolemBase.this.isInventoryChanged = true;\n\t\t\t}\n\t\t};\n\t\tif (old != null) {\n\t\t\tfinal int count = Math.min(old.getContainerSize(), this.inventory.getContainerSize());\n\t\t\tfor (int i = 0; i < count; ++i) {\n\t\t\t\tfinal ItemStack stack = old.getItem(i);\n\t\t\t\tif (!stack.isEmpty()) {\n\t\t\t\t\tthis.inventory.setItem(i, stack.copy());\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\t\tthis.isInventoryChanged = true;\n\t}\n\n\t@Override\n\tpublic boolean wantsToPickUp(final ServerLevel serverLevel, final ItemStack stack)''', s, count=1, flags=re.S)

s = s.replace('protected void dropEquipment() {\n\t\tsuper.dropEquipment();\n\t\tContainers.dropContents(this.level(), this.blockPosition(), this.inventory);\n\t}',
'''protected void dropEquipment(final ServerLevel serverLevel) {\n\t\tsuper.dropEquipment(serverLevel);\n\t\tContainers.dropContents(serverLevel, this.blockPosition(), this.inventory);\n\t}''')
s = s.replace('protected void pickUpItem(ItemEntity item) {\n\t\tInventoryCarrier.pickUpItem(this, this, item);\n\t}',
'''protected void pickUpItem(final ServerLevel serverLevel, final ItemEntity item) {\n\t\tInventoryCarrier.pickUpItem(serverLevel, this, this, item);\n\t}''')
# Remove obsolete listener callbacks; setChanged override now handles dirty state.
s = re.sub(r'\n\t@Override\n\tpublic void onItemPickup\(ItemEntity itemEntity\) \{.*?\n\t\}\n', '\n', s, count=1, flags=re.S)
s = re.sub(r'\n\t@Override\n\tpublic void containerChanged\(Container container\) \{.*?\n\t\}\n', '\n', s, count=1, flags=re.S)
p.write_text(s)

# Goals and simple behavior call sites that gained ServerLevel arguments.
p = ROOT / 'com/mcmoddev/golems/entity/goal/MoveToItemGoal.java'
if p.exists():
    s = p.read_text()
    s = s.replace('mob.wantsToPickUp(itemEntity.getItem())',
                  'mob.level() instanceof net.minecraft.server.level.ServerLevel serverLevel && mob.wantsToPickUp(serverLevel, itemEntity.getItem())')
    p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/data/behavior/WearBannerBehavior.java'
if p.exists():
    s = p.read_text()
    if 'import net.minecraft.server.level.ServerLevel;' not in s:
        s = s.replace('import net.minecraft.tags.ItemTags;\n', 'import net.minecraft.tags.ItemTags;\nimport net.minecraft.server.level.ServerLevel;\n')
    s = s.replace('mob.spawnAtLocation(banner, mob.getBbHeight() * 0.9F);',
                  'if (mob.level() instanceof ServerLevel serverLevel) {\n\t\t\t\tmob.spawnAtLocation(serverLevel, banner, mob.getBbHeight() * 0.9F);\n\t\t\t}')
    p.write_text(s)

# Mob pickup checks gained a ServerLevel argument.
p = ROOT / 'com/mcmoddev/golems/entity/goal/MoveToItemGoal.java'
if p.exists():
    s = p.read_text()
    s = s.replace('public void tick() {\n\t\t// make a list of itemstacks in nearby area',
                  'public void tick() {\n\t\tif (!(entity.level() instanceof net.minecraft.server.level.ServerLevel serverLevel)) {\n\t\t\treturn;\n\t\t}\n\t\t// make a list of itemstacks in nearby area')
    s = s.replace('entity.wantsToPickUp(e.getItem())', 'entity.wantsToPickUp(serverLevel, e.getItem())')
    p.write_text(s)

# Furnace burn times now require the Level-owned FuelValues object.
p = ROOT / 'com/mcmoddev/golems/data/behavior/UseFuelBehavior.java'
if p.exists():
    s = p.read_text()
    s = s.replace('stack.getBurnTime(RecipeType.SMELTING)', 'stack.getBurnTime(RecipeType.SMELTING, mob.level().fuelValues())')
    s = s.replace('stack.getCraftingRemainingItem()', 'stack.getCraftingRemainder()')
    p.write_text(s)

# The removed canAttackType helper is represented by LivingEntity-aware canAttack.
p = ROOT / 'com/mcmoddev/golems/data/behavior/AbstractShootBehavior.java'
if p.exists():
    s = p.read_text()
    s = s.replace('if (!mob.canAttackType(e.getType())) {', 'if (e instanceof LivingEntity living && !mob.canAttack(living)) {')
    p.write_text(s)

# BuiltInRegistries#get(Identifier) now yields an optional holder reference.
p = ROOT / 'com/mcmoddev/golems/util/DeferredBlockState.java'
if p.exists():
    s = p.read_text()
    s = s.replace('final Block block = BuiltInRegistries.BLOCK.get(this.block);',
                  'final Block block = BuiltInRegistries.BLOCK.get(this.block).map(holder -> holder.value()).orElse(null);')
    p.write_text(s)

# Catch stale behavior persistence symbols after the structured rewrite.
for p in ROOT.rglob('*.java'):
    s = p.read_text()
    if 'onWriteData(final IExtraGolem entity, final CompoundTag' in s:
        s = s.replace('onWriteData(final IExtraGolem entity, final CompoundTag tag)', 'onWriteData(final IExtraGolem entity, final ValueOutput output)')
    if 'onReadData(final IExtraGolem entity, final CompoundTag' in s:
        s = s.replace('onReadData(final IExtraGolem entity, final CompoundTag tag)', 'onReadData(final IExtraGolem entity, final ValueInput input)')
    p.write_text(s)

print('Applied Extra Golems 26.1 migration stage 3')
