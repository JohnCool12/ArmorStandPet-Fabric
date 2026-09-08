from pathlib import Path

reg = Path('project/src/main/java/com/mcmoddev/golems/EGRegistry.java')
s = reg.read_text()

# Blocks: Minecraft 26.1 requires the registry ResourceKey on BlockBehaviour.Properties
# before Block construction. Utility blocks construct their own Properties, so pass the key
# into their constructors and set it there.
s = s.replace(
'''\t\tpublic static final DeferredHolder<Block, Block> GOLEM_HEAD = BLOCKS.register("golem_head",\n\t\t\t\t() -> new GolemHeadBlock(Block.Properties.ofFullCopy(Blocks.CARVED_PUMPKIN)));\n\t\tpublic static final DeferredHolder<Block, GlowBlock> LIGHT_PROVIDER = BLOCKS.register("light_provider",\n\t\t\t\t() -> new GlowBlock(Blocks.GLASS, 1.0F));\n\t\tpublic static final DeferredHolder<Block, PowerBlock> POWER_PROVIDER = BLOCKS.register("power_provider",\n\t\t\t\t() -> new PowerBlock(15));\n''',
'''\t\tpublic static final DeferredHolder<Block, Block> GOLEM_HEAD = BLOCKS.register("golem_head",\n\t\t\t\t() -> new GolemHeadBlock(Block.Properties.ofFullCopy(Blocks.CARVED_PUMPKIN)\n\t\t\t\t\t\t.setId(ResourceKey.create(Registries.BLOCK, Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "golem_head")))));\n\t\tpublic static final DeferredHolder<Block, GlowBlock> LIGHT_PROVIDER = BLOCKS.register("light_provider",\n\t\t\t\t() -> new GlowBlock(Blocks.GLASS, 1.0F,\n\t\t\t\t\t\tResourceKey.create(Registries.BLOCK, Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "light_provider"))));\n\t\tpublic static final DeferredHolder<Block, PowerBlock> POWER_PROVIDER = BLOCKS.register("power_provider",\n\t\t\t\t() -> new PowerBlock(15,\n\t\t\t\t\t\tResourceKey.create(Registries.BLOCK, Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "power_provider"))));\n''')

# Items: Item.Properties also requires the registry ResourceKey before construction.
s = s.replace(
'''\t\tpublic static final DeferredHolder<Item, GolemSpellItem> GOLEM_SPELL = ITEMS.register("golem_spell",\n\t\t\t\t() -> new GolemSpellItem(new Item.Properties()));\n\t\tpublic static final DeferredHolder<Item, SpawnGolemItem> SPAWN_BEDROCK_GOLEM = ITEMS\n\t\t\t\t.register("spawn_bedrock_golem", () -> new SpawnGolemItem(new Item.Properties()));\n\t\tpublic static final DeferredHolder<Item, GuideBookItem> GUIDE_BOOK = ITEMS.register("guide_book",\n\t\t\t\t() -> new GuideBookItem(new Item.Properties().stacksTo(1)));\n\n\t\tpublic static final DeferredHolder<Item, Item> GOLEM_HEAD = ITEMS.register("golem_head",\n\t\t\t\t() -> new GolemHeadItem(BlockReg.GOLEM_HEAD.get(), new Item.Properties()));\n\t\tpublic static final DeferredHolder<Item, SpawnEggItem> GOLEM_SPAWN_EGG = ITEMS.register("golem_spawn_egg",\n\t\t\t\t() -> new SpawnEggItem(new Item.Properties().spawnEgg(EntityReg.GOLEM.get())));\n''',
'''\t\tpublic static final DeferredHolder<Item, GolemSpellItem> GOLEM_SPELL = ITEMS.register("golem_spell",\n\t\t\t\t() -> new GolemSpellItem(new Item.Properties()\n\t\t\t\t\t\t.setId(ResourceKey.create(Registries.ITEM, Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "golem_spell")))));\n\t\tpublic static final DeferredHolder<Item, SpawnGolemItem> SPAWN_BEDROCK_GOLEM = ITEMS\n\t\t\t\t.register("spawn_bedrock_golem", () -> new SpawnGolemItem(new Item.Properties()\n\t\t\t\t\t\t.setId(ResourceKey.create(Registries.ITEM, Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "spawn_bedrock_golem")))));\n\t\tpublic static final DeferredHolder<Item, GuideBookItem> GUIDE_BOOK = ITEMS.register("guide_book",\n\t\t\t\t() -> new GuideBookItem(new Item.Properties().stacksTo(1)\n\t\t\t\t\t\t.setId(ResourceKey.create(Registries.ITEM, Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "guide_book")))));\n\n\t\tpublic static final DeferredHolder<Item, Item> GOLEM_HEAD = ITEMS.register("golem_head",\n\t\t\t\t() -> new GolemHeadItem(BlockReg.GOLEM_HEAD.get(), new Item.Properties().useBlockDescriptionPrefix()\n\t\t\t\t\t\t.setId(ResourceKey.create(Registries.ITEM, Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "golem_head")))));\n\t\tpublic static final DeferredHolder<Item, SpawnEggItem> GOLEM_SPAWN_EGG = ITEMS.register("golem_spawn_egg",\n\t\t\t\t() -> new SpawnEggItem(new Item.Properties().spawnEgg(EntityReg.GOLEM.get())\n\t\t\t\t\t\t.setId(ResourceKey.create(Registries.ITEM, Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "golem_spawn_egg")))));\n''')

if '.setId(ResourceKey.create(Registries.BLOCK' not in s:
    raise SystemExit('Block registry ID patch did not apply')
if s.count('.setId(ResourceKey.create(Registries.ITEM') < 5:
    raise SystemExit('Item registry ID patch did not apply completely')
reg.write_text(s)

# Utility blocks need to attach their own IDs to the internally-created Properties.
glow = Path('project/src/main/java/com/mcmoddev/golems/block/GlowBlock.java')
g = glow.read_text()
if 'import net.minecraft.resources.ResourceKey;' not in g:
    g = g.replace('import net.minecraft.core.BlockPos;\n', 'import net.minecraft.core.BlockPos;\nimport net.minecraft.resources.ResourceKey;\n')
g = g.replace('public GlowBlock(final BlockBehaviour copy, final float defaultLight) {\n\t\tsuper(Properties.ofFullCopy(copy).randomTicks().lightLevel(state -> state.getValue(LIGHT_LEVEL)), UPDATE_TICKS);',
              'public GlowBlock(final BlockBehaviour copy, final float defaultLight, final ResourceKey<Block> id) {\n\t\tsuper(Properties.ofFullCopy(copy).setId(id).randomTicks().lightLevel(state -> state.getValue(LIGHT_LEVEL)), UPDATE_TICKS);')
if 'final ResourceKey<Block> id' not in g or '.setId(id)' not in g:
    raise SystemExit('GlowBlock registry key patch did not apply')
glow.write_text(g)

power = Path('project/src/main/java/com/mcmoddev/golems/block/PowerBlock.java')
p = power.read_text()
if 'import net.minecraft.resources.ResourceKey;' not in p:
    p = p.replace('import net.minecraft.core.Direction;\n', 'import net.minecraft.core.Direction;\nimport net.minecraft.resources.ResourceKey;\n')
p = p.replace('public PowerBlock(final int powerLevel) {\n\t\tsuper(Properties.ofFullCopy(Blocks.GLASS).randomTicks(), UPDATE_TICKS);',
              'public PowerBlock(final int powerLevel, final ResourceKey<Block> id) {\n\t\tsuper(Properties.ofFullCopy(Blocks.GLASS).setId(id).randomTicks(), UPDATE_TICKS);')
if 'final ResourceKey<Block> id' not in p or '.setId(id)' not in p:
    raise SystemExit('PowerBlock registry key patch did not apply')
power.write_text(p)

print('Applied pass 10: explicit 26.1 registry IDs for all Extra Golems blocks and items.')
