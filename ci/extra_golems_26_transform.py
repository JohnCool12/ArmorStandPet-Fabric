from pathlib import Path
import re

ROOT = Path('project/src/main/java')

# These are either documented 1.21.11/26.1 renames or 26.1.2 hotfix renames.
# ModForge runs first and applies every provable rename; these cover the later
# unobfuscated-era package shuffles / semantic adapters that cannot be chained exactly.
REPLACEMENTS = [
    ('net.minecraft.ResourceLocationException', 'net.minecraft.IdentifierException'),
    ('ResourceLocationException', 'IdentifierException'),
    ('net.minecraft.resources.ResourceLocation', 'net.minecraft.resources.Identifier'),
    ('ResourceLocation', 'Identifier'),
    ('net.minecraft.advancements.critereon.MinMaxBounds', 'net.minecraft.advancements.predicates.MinMaxBounds'),
    ('net.minecraft.advancements.criterion.MinMaxBounds', 'net.minecraft.advancements.predicates.MinMaxBounds'),
    ('net.minecraft.advancements.critereon', 'net.minecraft.advancements.criterion'),
    ('net.minecraft.Util', 'net.minecraft.util.Util'),
    ('net.minecraft.world.entity.MobSpawnType', 'net.minecraft.world.entity.EntitySpawnReason'),
    ('MobSpawnType', 'EntitySpawnReason'),
    ('net.minecraft.world.entity.animal.AbstractGolem', 'net.minecraft.world.entity.animal.golem.AbstractGolem'),
    ('net.minecraft.world.entity.animal.IronGolem', 'net.minecraft.world.entity.animal.golem.IronGolem'),
    ('net.minecraft.world.entity.animal.SnowGolem', 'net.minecraft.world.entity.animal.golem.SnowGolem'),
    ('net.minecraft.world.entity.npc.AbstractVillager', 'net.minecraft.world.entity.npc.villager.AbstractVillager'),
    ('net.minecraft.world.entity.npc.Villager', 'net.minecraft.world.entity.npc.villager.Villager'),
    ('net.minecraft.world.entity.projectile.AbstractArrow', 'net.minecraft.world.entity.projectile.arrow.AbstractArrow'),
    ('net.minecraft.world.entity.projectile.SmallFireball', 'net.minecraft.world.entity.projectile.hurtingprojectile.SmallFireball'),
    ('net.minecraft.world.entity.projectile.Snowball', 'net.minecraft.world.entity.projectile.throwableitemprojectile.Snowball'),
    ('net.minecraft.client.model.IronGolemModel', 'net.minecraft.client.model.animal.golem.IronGolemModel'),
    ('net.minecraft.client.renderer.RenderType', 'net.minecraft.client.renderer.rendertype.RenderType'),
    ('net.minecraft.client.renderer.RenderStateShard', 'net.minecraft.client.renderer.rendertype.RenderStateShard'),
    ('net.minecraft.client.gui.GuiGraphics', 'net.minecraft.client.gui.GuiGraphicsExtractor'),
    ('GuiGraphics', 'GuiGraphicsExtractor'),
]

for p in ROOT.rglob('*.java'):
    s = p.read_text()
    for a, b in REPLACEMENTS:
        s = s.replace(a, b)
    s = s.replace('EntitySpawnReason.SPAWN_EGG', 'EntitySpawnReason.SPAWN_ITEM_USE')
    p.write_text(s)

# ContainerListener was moved to the inventory package. Keep the listener contract;
# it is part of the golem inventory/update behavior and must not be stripped.
p = ROOT / 'com/mcmoddev/golems/entity/IExtraGolem.java'
s = p.read_text()
s = s.replace('import net.minecraft.world.ContainerListener;', 'import net.minecraft.world.inventory.ContainerListener;')
p.write_text(s)

# NeoForge 26.1 no longer exposes the old INBTSerializable contract used here.
# Keep the explicit provider-aware contract already used by the final V4 source.
p = ROOT / 'com/mcmoddev/golems/data/behavior/data/IBehaviorData.java'
p.write_text('''package com.mcmoddev.golems.data.behavior.data;\n\nimport net.minecraft.core.HolderLookup;\nimport net.minecraft.nbt.CompoundTag;\n\n/** Runtime data owned by one attached golem behavior. */\npublic interface IBehaviorData {\n    CompoundTag serializeNBT(HolderLookup.Provider provider);\n    void deserializeNBT(HolderLookup.Provider provider, CompoundTag tag);\n}\n''')

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

# DeferredSpawnEggItem was removed. 26.1 stores spawn-egg type in Item.Properties.
p = ROOT / 'com/mcmoddev/golems/EGRegistry.java'
s = p.read_text()
s = s.replace('import net.neoforged.neoforge.common.DeferredSpawnEggItem;\n', 'import net.minecraft.world.item.SpawnEggItem;\n')
s = s.replace('DeferredHolder<Item, DeferredSpawnEggItem> GOLEM_SPAWN_EGG', 'DeferredHolder<Item, SpawnEggItem> GOLEM_SPAWN_EGG')
s = s.replace('new DeferredSpawnEggItem(EntityReg.GOLEM, 0x9B9B9B, 0x4A7D2C, new Item.Properties())', 'new SpawnEggItem(new Item.Properties().spawnEgg(EntityReg.GOLEM.get()))')
p.write_text(s)

# Item#use now returns InteractionResult directly. Preserve the original guide-book
# behavior instead of stubbing it: the client still opens the same guide screen.
p = ROOT / 'com/mcmoddev/golems/item/GuideBookItem.java'
p.write_text('''package com.mcmoddev.golems.item;\n\nimport com.mcmoddev.golems.ClientHooks;\nimport net.minecraft.world.InteractionHand;\nimport net.minecraft.world.InteractionResult;\nimport net.minecraft.world.entity.player.Player;\nimport net.minecraft.world.item.Item;\nimport net.minecraft.world.item.ItemStack;\nimport net.minecraft.world.level.Level;\n\npublic class GuideBookItem extends Item {\n    public GuideBookItem(final Item.Properties properties) {\n        super(properties);\n    }\n\n    @Override\n    public InteractionResult use(Level level, Player player, InteractionHand hand) {\n        ItemStack stack = player.getItemInHand(hand);\n        if (level.isClientSide()) {\n            ClientHooks.openGuideBook(player, stack);\n        }\n        return InteractionResult.SUCCESS;\n    }\n}\n''')

# Any remaining legacy serialization imports are invalid on this target.
for p in ROOT.rglob('*.java'):
    s = p.read_text()
    s = re.sub(r'^import net\.neoforged\.neoforge\.common\.util\.INBTSerializable;\n', '', s, flags=re.M)
    p.write_text(s)

print('Applied Extra Golems 26.1 semantic migration pass')
