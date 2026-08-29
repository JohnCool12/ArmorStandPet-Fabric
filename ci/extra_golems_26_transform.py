from pathlib import Path
import re

ROOT = Path('project/src/main/java')

REPLACEMENTS = [
    ('net.minecraft.ResourceLocationException', 'net.minecraft.IdentifierException'),
    ('ResourceLocationException', 'IdentifierException'),
    ('net.minecraft.resources.ResourceLocation', 'net.minecraft.resources.Identifier'),
    ('ResourceLocation', 'Identifier'),
    ('net.minecraft.advancements.critereon', 'net.minecraft.advancements.criterion'),
    ('net.minecraft.world.entity.MobSpawnType', 'net.minecraft.world.entity.EntitySpawnReason'),
    ('MobSpawnType', 'EntitySpawnReason'),
    ('net.minecraft.world.entity.animal.AbstractGolem', 'net.minecraft.world.entity.animal.golem.AbstractGolem'),
    ('net.minecraft.world.entity.animal.IronGolem', 'net.minecraft.world.entity.animal.golem.IronGolem'),
    ('net.minecraft.world.entity.animal.SnowGolem', 'net.minecraft.world.entity.animal.golem.SnowGolem'),
]

for p in ROOT.rglob('*.java'):
    s = p.read_text()
    for a, b in REPLACEMENTS:
        s = s.replace(a, b)
    s = s.replace('EntitySpawnReason.SPAWN_EGG', 'EntitySpawnReason.SPAWN_ITEM_USE')
    p.write_text(s)

# 26.1 removed ContainerListener from this abstraction; SimpleContainer remains the actual inventory object.
p = ROOT / 'com/mcmoddev/golems/entity/IExtraGolem.java'
s = p.read_text()
s = re.sub(r'^import net\.minecraft\.world\.ContainerListener;\n', '', s, flags=re.M)
s = s.replace(', ContainerListener,', ',')
s = s.replace('ContainerListener, ', '')
s = s.replace(', ContainerListener', '')
p.write_text(s)

# NeoForge 26.1 removed INBTSerializable. Keep the same explicit provider-aware contract used by the final V4 source.
p = ROOT / 'com/mcmoddev/golems/data/behavior/data/IBehaviorData.java'
p.write_text('''package com.mcmoddev.golems.data.behavior.data;\n\nimport net.minecraft.core.HolderLookup;\nimport net.minecraft.nbt.CompoundTag;\n\n/** Runtime data owned by one attached golem behavior. */\npublic interface IBehaviorData {\n    CompoundTag serializeNBT(HolderLookup.Provider provider);\n    void deserializeNBT(HolderLookup.Provider provider, CompoundTag tag);\n}\n''')

# Update the three behavior-data implementations to the provider-aware serialization ABI.
for rel in [
    'com/mcmoddev/golems/data/behavior/data/ExplodeBehaviorData.java',
    'com/mcmoddev/golems/data/behavior/data/ShootBehaviorData.java',
    'com/mcmoddev/golems/data/behavior/data/UseFuelBehaviorData.java',
]:
    p = ROOT / rel
    s = p.read_text()
    s = s.replace('public CompoundTag serializeNBT()', 'public CompoundTag serializeNBT(net.minecraft.core.HolderLookup.Provider provider)')
    s = s.replace('public void deserializeNBT(CompoundTag tag)', 'public void deserializeNBT(net.minecraft.core.HolderLookup.Provider provider, CompoundTag tag)')
    s = s.replace('public void deserializeNBT(final CompoundTag tag)', 'public void deserializeNBT(net.minecraft.core.HolderLookup.Provider provider, final CompoundTag tag)')
    p.write_text(s)

# DeferredSpawnEggItem was removed. 26.1 encodes its entity type directly in Item.Properties.
p = ROOT / 'com/mcmoddev/golems/EGRegistry.java'
s = p.read_text()
s = s.replace('import net.neoforged.neoforge.common.DeferredSpawnEggItem;\n', 'import net.minecraft.world.item.SpawnEggItem;\n')
s = s.replace('DeferredHolder<Item, DeferredSpawnEggItem> GOLEM_SPAWN_EGG', 'DeferredHolder<Item, SpawnEggItem> GOLEM_SPAWN_EGG')
s = s.replace('new DeferredSpawnEggItem(EntityReg.GOLEM, 0x9B9B9B, 0x4A7D2C, new Item.Properties())', 'new SpawnEggItem(new Item.Properties().spawnEgg(EntityReg.GOLEM.get()))')
p.write_text(s)

# 26.1 Item#use returns InteractionResult. Keep guidebook server semantics compiling first;
# the client screen hook is restored after the native baseline is compiling.
p = ROOT / 'com/mcmoddev/golems/item/GuideBookItem.java'
p.write_text('''package com.mcmoddev.golems.item;\n\nimport net.minecraft.world.InteractionHand;\nimport net.minecraft.world.InteractionResult;\nimport net.minecraft.world.entity.player.Player;\nimport net.minecraft.world.item.Item;\nimport net.minecraft.world.level.Level;\n\npublic class GuideBookItem extends Item {\n    public GuideBookItem(final Item.Properties properties) {\n        super(properties);\n    }\n\n    @Override\n    public InteractionResult use(Level level, Player player, InteractionHand hand) {\n        return InteractionResult.SUCCESS;\n    }\n}\n''')

# Remove now-obsolete INBTSerializable imports/implements if any secondary classes carried them.
for p in ROOT.rglob('*.java'):
    s = p.read_text()
    s = re.sub(r'^import net\.neoforged\.neoforge\.common\.util\.INBTSerializable;\n', '', s, flags=re.M)
    p.write_text(s)

print('Applied initial Extra Golems 26.1 migration pass')
