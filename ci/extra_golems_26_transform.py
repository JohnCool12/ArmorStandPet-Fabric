from pathlib import Path
import re

ROOT = Path('project/src/main/java')


def token_replace(text: str, old: str, new: str) -> str:
    return re.sub(r'(?<![A-Za-z0-9_$])' + re.escape(old) + r'(?![A-Za-z0-9_$])', new, text)


FQ_REPLACEMENTS = [
    ('net.minecraft.ResourceLocationException', 'net.minecraft.IdentifierException'),
    ('net.minecraft.resources.ResourceLocation', 'net.minecraft.resources.Identifier'),
    ('net.minecraft.advancements.critereon.MinMaxBounds', 'net.minecraft.advancements.criterion.MinMaxBounds'),
    ('net.minecraft.advancements.predicates.MinMaxBounds', 'net.minecraft.advancements.criterion.MinMaxBounds'),
    ('net.minecraft.advancements.critereon', 'net.minecraft.advancements.criterion'),
    ('net.minecraft.Util', 'net.minecraft.util.Util'),
    ('net.minecraft.world.entity.MobSpawnType', 'net.minecraft.world.entity.EntitySpawnReason'),
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
]
TOKEN_REPLACEMENTS = [
    ('ResourceLocationException', 'IdentifierException'),
    ('ResourceLocation', 'Identifier'),
    ('MobSpawnType', 'EntitySpawnReason'),
    ('GuiGraphics', 'GuiGraphicsExtractor'),
]

for p in ROOT.rglob('*.java'):
    s = p.read_text()
    for a, b in FQ_REPLACEMENTS:
        s = s.replace(a, b)
    for a, b in TOKEN_REPLACEMENTS:
        s = token_replace(s, a, b)
    s = s.replace('EntitySpawnReason.SPAWN_EGG', 'EntitySpawnReason.SPAWN_ITEM_USE')
    s = s.replace('.registryOrThrow(', '.lookupOrThrow(')
    s = s.replace('.getHolderOrThrow(', '.getOrThrow(')
    p.write_text(s)

for rel in [
    'com/mcmoddev/golems/ExtraGolems.java',
    'com/mcmoddev/golems/EGEvents.java',
    'com/mcmoddev/golems/block/GolemHeadBlock.java',
]:
    p = ROOT / rel
    if p.exists():
        s = p.read_text().replace('.location()', '.identifier()')
        p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/ExtraGolems.java'
s = p.read_text().replace('FMLEnvironment.dist', 'FMLEnvironment.getDist()')
p.write_text(s)

for p in ROOT.rglob('*.java'):
    s = p.read_text()
    s = re.sub(r'\.isClientSide(?!\s*\()', '.isClientSide()', s)
    for var in ('world', 'level', 'pLevel', 'serverLevel'):
        s = re.sub(r'\b' + var + r'\.random\b', var + '.getRandom()', s)
    p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/entity/IExtraGolem.java'
s = p.read_text()
s = s.replace('pCompound.contains(KEY_GOLEM_ID, Tag.TAG_STRING)', 'pCompound.contains(KEY_GOLEM_ID)')
s = s.replace('pCompound.getString(KEY_GOLEM_ID)', 'pCompound.getStringOr(KEY_GOLEM_ID, "")')
s = s.replace('pCompound.contains("Material", Tag.TAG_STRING)', 'pCompound.contains("Material")')
s = s.replace('pCompound.getString("Material")', 'pCompound.getStringOr("Material", "")')
s = s.replace('import net.minecraft.nbt.Tag;\n', '')
p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/entity/IVariantProvider.java'
s = p.read_text()
s = s.replace('tag.contains(KEY_VARIANT, Tag.TAG_BYTE)', 'tag.contains(KEY_VARIANT)')
s = s.replace('tag.getByte(KEY_VARIANT)', 'tag.getByteOr(KEY_VARIANT, (byte) 0)')
s = s.replace('import net.minecraft.nbt.Tag;\n', '')
p.write_text(s)

for rel, replacements in {
    'com/mcmoddev/golems/data/behavior/data/UseFuelBehaviorData.java': [('tag.getInt(KEY_FUEL)', 'tag.getIntOr(KEY_FUEL, 0)')],
    'com/mcmoddev/golems/data/behavior/data/ExplodeBehaviorData.java': [
        ('tag.getInt(KEY_FUSE)', 'tag.getIntOr(KEY_FUSE, 0)'),
        ('tag.getBoolean(KEY_FUSE_LIT)', 'tag.getBooleanOr(KEY_FUSE_LIT, false)'),
    ],
    'com/mcmoddev/golems/data/behavior/AbstractShootBehavior.java': [('tag.getInt(KEY_AMMO)', 'tag.getIntOr(KEY_AMMO, 0)')],
    'com/mcmoddev/golems/data/behavior/UseFuelBehavior.java': [('tag.getCompound(KEY_FUEL_HELPER)', 'tag.getCompoundOrEmpty(KEY_FUEL_HELPER)')],
    'com/mcmoddev/golems/data/behavior/ExplodeBehavior.java': [('tag.getCompound(KEY_EXPLOSION_HELPER)', 'tag.getCompound(KEY_EXPLOSION_HELPER).orElseGet(CompoundTag::new)')],
}.items():
    p = ROOT / rel
    if p.exists():
        s = p.read_text()
        for a, b in replacements:
            s = s.replace(a, b)
        p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/data/golem/BuildingBlocks.java'
s = p.read_text().replace('BuiltInRegistries.BLOCK.get(id)', 'BuiltInRegistries.BLOCK.getValue(id)')
p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/util/DeferredHolderSet.java'
s = p.read_text()
s = s.replace('registry.getOrCreateTag(either.left().get())', 'registry.getOrThrow(either.left().get())')
s = s.replace('registry.getHolder(key)', 'registry.get(key)')
p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/EGEvents.java'
s = p.read_text().replace('registry.getOrCreateTag(VILLAGER_SUMMONABLE)', 'registry.getOrThrow(VILLAGER_SUMMONABLE)')
p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/data/golem/Attributes.java'
s = p.read_text()
s = s.replace('PathType.DAMAGE_FIRE', 'PathType.FIRE')
s = s.replace('PathType.DANGER_FIRE', 'PathType.FIRE_IN_NEIGHBOR')
p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/data/model/Layer.java'
s = p.read_text().replace(
    'this.colors = Vec3.fromRGB24(color);',
    'this.colors = new Vec3(((color >> 16) & 255) / 255.0D, ((color >> 8) & 255) / 255.0D, (color & 255) / 255.0D);')
p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/client/entity/layer/GolemLayerListLayer.java'
if p.exists():
    s = p.read_text().replace(
        'Vec3.fromRGB24(entity.getBiomeColor()).toVector3f()',
        'new Vec3(((entity.getBiomeColor() >> 16) & 255) / 255.0D, ((entity.getBiomeColor() >> 8) & 255) / 255.0D, (entity.getBiomeColor() & 255) / 255.0D).toVector3f()')
    p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/block/GolemHeadBlock.java'
s = p.read_text()
s = s.replace('EntityType.IRON_GOLEM.create(level)', 'EntityType.IRON_GOLEM.create(level, EntitySpawnReason.MOB_SUMMONED)')
s = s.replace('ironGolem.moveTo(spawnX, spawnY, spawnZ, 0.0F, 0.0F)', 'ironGolem.snapTo(spawnX, spawnY, spawnZ, 0.0F, 0.0F)')
s = s.replace('golem.moveTo(spawnX, spawnY, spawnZ, 0.0F, 0.0F)', 'golem.snapTo(spawnX, spawnY, spawnZ, 0.0F, 0.0F)')
if 'import net.minecraft.world.entity.EntitySpawnReason;' not in s:
    s = s.replace('import net.minecraft.world.entity.EntityType;\n', 'import net.minecraft.world.entity.EntityType;\nimport net.minecraft.world.entity.EntitySpawnReason;\n')
p.write_text(s)

p = ROOT / 'com/mcmoddev/golems/entity/IExtraGolem.java'
s = p.read_text().replace('import net.minecraft.world.ContainerListener;', 'import net.minecraft.world.inventory.ContainerListener;')
p.write_text(s)

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

p = ROOT / 'com/mcmoddev/golems/EGRegistry.java'
s = p.read_text()
s = s.replace('import net.neoforged.neoforge.common.DeferredSpawnEggItem;\n', 'import net.minecraft.world.item.SpawnEggItem;\n')
s = s.replace('DeferredHolder<Item, DeferredSpawnEggItem> GOLEM_SPAWN_EGG', 'DeferredHolder<Item, SpawnEggItem> GOLEM_SPAWN_EGG')
s = s.replace('new DeferredSpawnEggItem(EntityReg.GOLEM, 0x9B9B9B, 0x4A7D2C, new Item.Properties())', 'new SpawnEggItem(new Item.Properties().spawnEgg(EntityReg.GOLEM.get()))')
p.write_text(s)

# Preserve the native NeoForge guide-book opener while adopting the new Item#use result type.
p = ROOT / 'com/mcmoddev/golems/item/GuideBookItem.java'
p.write_text('''package com.mcmoddev.golems.item;\n\nimport com.mcmoddev.golems.client.EGClientEvents;\nimport net.minecraft.world.InteractionHand;\nimport net.minecraft.world.InteractionResult;\nimport net.minecraft.world.entity.player.Player;\nimport net.minecraft.world.item.Item;\nimport net.minecraft.world.item.ItemStack;\nimport net.minecraft.world.level.Level;\n\npublic class GuideBookItem extends Item {\n    public GuideBookItem(final Item.Properties properties) { super(properties); }\n\n    @Override\n    public InteractionResult use(Level level, Player player, InteractionHand hand) {\n        ItemStack stack = player.getItemInHand(hand);\n        if (player.getCommandSenderWorld().isClientSide()) {\n            EGClientEvents.ForgeHandler.loadBookGui(player, stack);\n        }\n        return InteractionResult.SUCCESS;\n    }\n}\n''')

for p in ROOT.rglob('*.java'):
    s = p.read_text()
    s = re.sub(r'^import net\.neoforged\.neoforge\.common\.util\.INBTSerializable;\n', '', s, flags=re.M)
    p.write_text(s)

for p in ROOT.rglob('*.java'):
    s = p.read_text()
    assert 'GuiGraphicsExtractorExtractor' not in s, p
    assert 'net.minecraft.advancements.predicates.MinMaxBounds' not in s, p

print('Applied proven common + idempotent Extra Golems 26.1 migration pass')
