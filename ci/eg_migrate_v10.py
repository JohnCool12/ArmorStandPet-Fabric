#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else 'work').resolve()
SRC = ROOT / 'src/main/java'

def patch(rel, pairs):
    p = SRC / rel
    s = p.read_text()
    for old, new in pairs:
        if old not in s:
            raise SystemExit(f'Missing expected registry-id source in {rel}: {old[:160]!r}')
        s = s.replace(old, new)
    p.write_text(s)

BLOCK_KEY = 'ResourceKey.create(net.minecraft.core.registries.Registries.BLOCK, net.minecraft.resources.Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "%s"))'
ITEM_KEY = 'ResourceKey.create(net.minecraft.core.registries.Registries.ITEM, net.minecraft.resources.Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "%s"))'

# 26.1 requires BlockBehaviour.Properties#setId before Block construction.
patch('com/mcmoddev/golems/EGRegistry.java', [
    ('() -> new GolemHeadBlock(Block.Properties.ofFullCopy(Blocks.CARVED_PUMPKIN))',
     '() -> new GolemHeadBlock(Block.Properties.ofFullCopy(Blocks.CARVED_PUMPKIN).setId(' + (BLOCK_KEY % 'golem_head') + '))'),
    ('() -> new GlowBlock(Blocks.GLASS, 1.0F)',
     '() -> new GlowBlock(Blocks.GLASS, 1.0F, ' + (BLOCK_KEY % 'light_provider') + ')'),
    ('() -> new PowerBlock(15)',
     '() -> new PowerBlock(15, ' + (BLOCK_KEY % 'power_provider') + ')'),

    # 26.1 likewise requires Item.Properties#setId before Item construction.
    ('() -> new GolemSpellItem(new Item.Properties())',
     '() -> new GolemSpellItem(new Item.Properties().setId(' + (ITEM_KEY % 'golem_spell') + '))'),
    ('() -> new SpawnGolemItem(new Item.Properties())',
     '() -> new SpawnGolemItem(new Item.Properties().setId(' + (ITEM_KEY % 'spawn_bedrock_golem') + '))'),
    ('() -> new GuideBookItem(new Item.Properties().stacksTo(1))',
     '() -> new GuideBookItem(new Item.Properties().stacksTo(1).setId(' + (ITEM_KEY % 'guide_book') + '))'),
    ('() -> new GolemHeadItem(BlockReg.GOLEM_HEAD.get(), new Item.Properties())',
     '() -> new GolemHeadItem(BlockReg.GOLEM_HEAD.get(), new Item.Properties().useBlockDescriptionPrefix().setId(' + (ITEM_KEY % 'golem_head') + '))'),
    ('() -> new DeferredSpawnEggItem(EntityReg.GOLEM, 0x9B9B9B, 0x4A7D2C, new Item.Properties())',
     '() -> new DeferredSpawnEggItem(EntityReg.GOLEM, 0x9B9B9B, 0x4A7D2C, new Item.Properties().setId(' + (ITEM_KEY % 'golem_spawn_egg') + '))'),
])

# These utility blocks create their Block.Properties internally, so the registry key
# has to be threaded into the constructor before super(...) constructs the Block.
patch('com/mcmoddev/golems/block/GlowBlock.java', [
    ('public GlowBlock(final BlockBehaviour copy, final float defaultLight) {\n\t\tsuper(Properties.ofFullCopy(copy).randomTicks().lightLevel(state -> state.getValue(LIGHT_LEVEL)), UPDATE_TICKS);',
     'public GlowBlock(final BlockBehaviour copy, final float defaultLight, final net.minecraft.resources.ResourceKey<Block> id) {\n\t\tsuper(Properties.ofFullCopy(copy).setId(id).randomTicks().lightLevel(state -> state.getValue(LIGHT_LEVEL)), UPDATE_TICKS);'),
])
patch('com/mcmoddev/golems/block/PowerBlock.java', [
    ('public PowerBlock(final int powerLevel) {\n\t\tsuper(Properties.ofFullCopy(Blocks.GLASS).randomTicks(), UPDATE_TICKS);',
     'public PowerBlock(final int powerLevel, final net.minecraft.resources.ResourceKey<Block> id) {\n\t\tsuper(Properties.ofFullCopy(Blocks.GLASS).setId(id).randomTicks(), UPDATE_TICKS);'),
])

print('Applied Minecraft 26.1 block/item registry-id migration pass 10')
