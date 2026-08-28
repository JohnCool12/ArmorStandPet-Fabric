#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "work").resolve()
SRC = ROOT / "src/main/java"

def replace_file(path: Path, replacements):
    if not path.exists():
        return
    s = path.read_text()
    original = s
    for old, new in replacements:
        s = s.replace(old, new)
    if s != original:
        path.write_text(s)

# ---- Exact 26.1.2 build toolchain ----
build = ROOT / "build.gradle"
s = build.read_text()
s = s.replace("id 'net.neoforged.moddev' version '2.0.107'", "id 'net.neoforged.moddev' version '2.0.144'")
s = s.replace('java.toolchain.languageVersion = JavaLanguageVersion.of(21)', 'java.toolchain.languageVersion = JavaLanguageVersion.of(25)')
start = s.find('    parchment {')
if start >= 0:
    end = s.find('\n    // Access Transformers', start)
    if end < 0:
        raise SystemExit('Could not locate end of parchment block')
    s = s[:start] + s[end:]
dep_start = s.find('dependencies {')
dep_end = s.find('\n}\n\n// This block of code expands', dep_start)
if dep_start < 0 or dep_end < 0:
    raise SystemExit('Could not locate dependencies block')
s = s[:dep_start] + 'dependencies {\n}\n' + s[dep_end + 2:]
s += '''\ntasks.withType(JavaCompile).configureEach {\n    options.compilerArgs += ['-Xmaxerrs', '1000']\n}\n'''
build.write_text(s)

gp = ROOT / "gradle.properties"
replacements = {
    'minecraft_version': '26.1.2',
    'minecraft_version_range': '[26.1.2]',
    'neo_version': '26.1.2.95',
    'mod_version': '26.1.2-clean-port-dev',
}
out = []
for line in gp.read_text().splitlines():
    key = line.split('=', 1)[0] if '=' in line else ''
    if key in replacements:
        line = f'{key}={replacements[key]}'
    if key in {'parchment_minecraft_version', 'parchment_mappings_version', 'top_proj', 'top_file', 'jade_proj', 'jade_file'}:
        continue
    out.append(line)
gp.write_text('\n'.join(out) + '\n')

wrapper = ROOT / "gradle/wrapper/gradle-wrapper.properties"
w = wrapper.read_text()
w = re.sub(r'gradle-[0-9.]+-bin\.zip', 'gradle-9.2.1-bin.zip', w)
wrapper.write_text(w)

# ---- Optional HUD integrations: compile core first ----
shutil.rmtree(SRC / "com/mcmoddev/golems/integration", ignore_errors=True)
extra = SRC / "com/mcmoddev/golems/ExtraGolems.java"
e = extra.read_text()
for needle in [
    'import com.mcmoddev.golems.integration.AddonLoader;\n',
    'import net.neoforged.fml.InterModComms;\n',
    'import net.neoforged.fml.ModList;\n',
    '\t\tAddonLoader.register(modEventBus);\n',
    '\t\tmodEventBus.addListener(ExtraGolems::enqueueIMC);\n',
]:
    e = e.replace(needle, '')
a = e.find('\n\tprivate static void enqueueIMC(')
if a >= 0:
    b = e.find('\n\tprivate static void loadConfig', a)
    if b < 0:
        raise SystemExit('Could not locate end of enqueueIMC')
    e = e[:a] + e[b:]
extra.write_text(e)

# ---- Broad Mojang 26.1 naming/package migrations ----
broad = [
    ('net.minecraft.ResourceLocationException', 'net.minecraft.IdentifierException'),
    ('ResourceLocationException', 'IdentifierException'),
    ('net.minecraft.resources.ResourceLocation', 'net.minecraft.resources.Identifier'),
    ('net.minecraft.advancements.critereon', 'net.minecraft.advancements.criterion'),
    ('net.minecraft.world.ContainerListener', 'net.minecraft.world.inventory.ContainerListener'),
    ('net.minecraft.world.entity.animal.AbstractGolem', 'net.minecraft.world.entity.animal.golem.AbstractGolem'),
    ('net.minecraft.world.entity.animal.IronGolem', 'net.minecraft.world.entity.animal.golem.IronGolem'),
    ('net.minecraft.world.entity.animal.SnowGolem', 'net.minecraft.world.entity.animal.golem.SnowGolem'),
    ('net.minecraft.world.entity.npc.AbstractVillager', 'net.minecraft.world.entity.npc.villager.AbstractVillager'),
    ('net.minecraft.world.entity.npc.Villager', 'net.minecraft.world.entity.npc.villager.Villager'),
    ('net.minecraft.Util', 'net.minecraft.util.Util'),
    ('net.minecraft.world.entity.projectile.AbstractArrow', 'net.minecraft.world.entity.projectile.arrow.AbstractArrow'),
    ('net.minecraft.world.entity.projectile.SmallFireball', 'net.minecraft.world.entity.projectile.hurtingprojectile.SmallFireball'),
    ('net.minecraft.world.entity.projectile.Snowball', 'net.minecraft.world.entity.projectile.throwableitemprojectile.Snowball'),
    ('net.minecraft.commands.arguments.ResourceLocationArgument', 'net.minecraft.commands.arguments.IdentifierArgument'),
    ('ResourceLocationArgument', 'IdentifierArgument'),
    ('MobSpawnType', 'EntitySpawnReason'),
]
for p in SRC.rglob('*.java'):
    text = p.read_text()
    for old, new in broad:
        text = text.replace(old, new)
    text = re.sub(r'\bResourceLocation\b', 'Identifier', text)
    text = re.sub(r'\.location\(\)', '.identifier()', text)
    text = text.replace('.registryOrThrow(', '.lookupOrThrow(')
    text = text.replace('.getHolderOrThrow(', '.getOrThrow(')
    text = text.replace('PathType.DAMAGE_FIRE', 'PathType.FIRE')
    text = text.replace('PathType.DANGER_FIRE', 'PathType.FIRE_IN_NEIGHBOR')
    p.write_text(text)

replace_file(SRC / "com/mcmoddev/golems/ExtraGolems.java", [
    ('FMLEnvironment.dist == Dist.CLIENT', 'FMLEnvironment.getDist() == Dist.CLIENT'),
])

# ---- Removed NeoForge INBTSerializable ----
ibd = SRC / "com/mcmoddev/golems/data/behavior/data/IBehaviorData.java"
ibd.write_text('''package com.mcmoddev.golems.data.behavior.data;\n\nimport com.mcmoddev.golems.entity.IExtraGolem;\nimport net.minecraft.core.HolderLookup;\nimport net.minecraft.nbt.CompoundTag;\n\n/** Per-golem behavior state. */\npublic interface IBehaviorData {\n    CompoundTag serializeNBT(HolderLookup.Provider provider);\n    void deserializeNBT(HolderLookup.Provider provider, CompoundTag tag);\n}\n''')

# ---- 26.1.2 Item interaction result API ----
guide = SRC / "com/mcmoddev/golems/item/GuideBookItem.java"
g = guide.read_text()
g = g.replace('import net.minecraft.world.InteractionResultHolder;\n', '')
g = g.replace('public InteractionResultHolder<ItemStack> use(Level worldIn, Player playerIn, InteractionHand handIn)',
              'public InteractionResult use(Level worldIn, Player playerIn, InteractionHand handIn)')
g = g.replace('return new InteractionResultHolder<>(InteractionResult.SUCCESS, itemstack);', 'return InteractionResult.SUCCESS;')
guide.write_text(g)

# ---- 26.1.2 spawn egg ----
registry = SRC / "com/mcmoddev/golems/EGRegistry.java"
r = registry.read_text()
r = r.replace('import net.neoforged.neoforge.common.DeferredSpawnEggItem;', 'import net.minecraft.world.item.SpawnEggItem;')
r = r.replace('DeferredHolder<Item, DeferredSpawnEggItem>', 'DeferredHolder<Item, SpawnEggItem>')
r = re.sub(
    r'\(\) -> new DeferredSpawnEggItem\(EntityReg\.GOLEM,\s*0x[0-9A-Fa-f]+,\s*0x[0-9A-Fa-f]+,\s*new Item\.Properties\(\)\)',
    '() -> new SpawnEggItem(new Item.Properties().spawnEgg(EntityReg.GOLEM.get()))',
    r,
)
r = r.replace('.build("golem"));',
              '.build(ResourceKey.create(net.minecraft.core.registries.Registries.ENTITY_TYPE, Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "golem"))));')
registry.write_text(r)

# ---- NBT 26.1 optional getters ----
iextra = SRC / "com/mcmoddev/golems/entity/IExtraGolem.java"
x = iextra.read_text()
x = re.sub(r'pCompound\.contains\(([^,]+),\s*Tag\.TAG_[A-Z_]+\)', r'pCompound.contains(\1)', x)
x = x.replace('Identifier.parse(pCompound.getString(KEY_GOLEM_ID))',
              'Identifier.parse(pCompound.getStringOr(KEY_GOLEM_ID, ""))')
x = x.replace('Identifier.parse(pCompound.getString("Material"))',
              'Identifier.parse(pCompound.getStringOr("Material", ""))')
iextra.write_text(x)

ivar = SRC / "com/mcmoddev/golems/entity/IVariantProvider.java"
v = ivar.read_text()
v = re.sub(r'tag\.contains\(([^,]+),\s*Tag\.TAG_[A-Z_]+\)', r'tag.contains(\1)', v)
v = v.replace('setVariant(tag.getByte(KEY_VARIANT));', 'setVariant(tag.getByteOr(KEY_VARIANT, (byte)0));')
ivar.write_text(v)

gbase = SRC / "com/mcmoddev/golems/entity/GolemBase.java"
gb = gbase.read_text()
gb = gb.replace('tag.getBoolean(KEY_CHILD)', 'tag.getBooleanOr(KEY_CHILD, false)')
gb = gb.replace('tag.getList("Inventory", 10)', 'tag.getListOrEmpty("Inventory")')
gb = gb.replace('EntitySpawnReason.SPAWN_EGG', 'EntitySpawnReason.SPAWN_ITEM_USE')
gbase.write_text(gb)

# ---- registry value APIs ----
replace_file(SRC / "com/mcmoddev/golems/data/golem/BuildingBlocks.java", [
    ('BuiltInRegistries.BLOCK.get(id)', 'BuiltInRegistries.BLOCK.getValue(id)')
])

dhs = SRC / "com/mcmoddev/golems/util/DeferredHolderSet.java"
d = dhs.read_text()
d = d.replace('registry.getOrCreateTag(either.left().get())', 'registry.getOrThrow(either.left().get())')
d = d.replace('registry.getHolder(key)', 'registry.get(key)')
dhs.write_text(d)

replace_file(SRC / "com/mcmoddev/golems/data/model/LayerList.java", [
    ('registry.getOrThrow(key)', 'registry.getValueOrThrow(key)')
])

replace_file(SRC / "com/mcmoddev/golems/data/model/Layer.java", [
    ('Vec3.fromRGB24(color)',
     'new Vec3((double)((color >> 16) & 255) / 255.0D, (double)((color >> 8) & 255) / 255.0D, (double)(color & 255) / 255.0D)')
])

replace_file(SRC / "com/mcmoddev/golems/data/behavior/util/GolemPredicate.java", [
    ('e.asMob().level().isDay()', 'e.asMob().level().getSkyDarken() < 4'),
    ('e.asMob().level().isNight()', 'e.asMob().level().getSkyDarken() >= 4'),
    ('e.asMob().isInWaterRainOrBubble()', '(e.asMob().isInWaterOrBubble() || e.asMob().isInRain())'),
])

# ---- UtilityBlock 26.1 block hooks ----
ub = SRC / "com/mcmoddev/golems/block/UtilityBlock.java"
u = ub.read_text()
u = u.replace('.noCollission()', '.noCollision()')
u = re.sub(
    r'@Override\s+public BlockState updateShape\(BlockState pState, Direction pFacing, BlockState pFacingState, LevelAccessor pLevel, BlockPos pCurrentPos, BlockPos pFacingPos\) \{.*?\n\t\}',
    '''@Override\n\tprotected BlockState updateShape(BlockState pState, net.minecraft.world.level.LevelReader pLevel,\n\t\t\tnet.minecraft.world.ticks.ScheduledTickAccess scheduledTicks, BlockPos pCurrentPos,\n\t\t\tDirection pFacing, BlockPos pFacingPos, BlockState pFacingState, RandomSource random) {\n\t\tif (pState.getValue(WATERLOGGED)) {\n\t\t\tscheduledTicks.scheduleTick(pCurrentPos, Fluids.WATER, Fluids.WATER.getTickDelay(pLevel));\n\t\t}\n\t\treturn super.updateShape(pState, pLevel, scheduledTicks, pCurrentPos, pFacing, pFacingPos, pFacingState, random);\n\t}''',
    u, flags=re.S)
u = u.replace('public ItemStack getCloneItemStack(final net.minecraft.world.level.LevelReader level, final BlockPos pos, final BlockState state) {',
              'protected ItemStack getCloneItemStack(final net.minecraft.world.level.LevelReader level, final BlockPos pos, final BlockState state, final boolean includeData) {')
u = u.replace('public VoxelShape getShape(', 'protected VoxelShape getShape(')
u = u.replace('public boolean canBeReplaced(final BlockState state, final BlockPlaceContext useContext) {',
              'protected boolean canBeReplaced(final BlockState state, final BlockPlaceContext useContext) {')
u = u.replace('public RenderShape getRenderShape(final BlockState state) {',
              'protected RenderShape getRenderShape(final BlockState state) {')
u = re.sub(r'\n\t@Override\n\tpublic void fallOn\(.*?\n\t\}', '', u, flags=re.S)
u = re.sub(r'\n\t@Override\n\tpublic void entityInside\(.*?\n\t\}', '', u, flags=re.S)
u = re.sub(r'\n\t@Override\n\tpublic void updateEntityAfterFallOn\(.*?\n\t\}', '', u, flags=re.S)
u = re.sub(r'\n\t@Override\n\tpublic boolean isPossibleToRespawnInThis\(.*?\n\t\}', '', u, flags=re.S)
ub.write_text(u)

# ContainerListener gained dataChanged.
gbase = SRC / "com/mcmoddev/golems/entity/GolemBase.java"
gb = gbase.read_text()
if 'dataChanged(net.minecraft.world.inventory.AbstractContainerMenu' not in gb:
    marker = '\n\t@Override\n\tpublic void containerChanged(Container container) {'
    ins = '''\n\t@Override\n\tpublic void dataChanged(net.minecraft.world.inventory.AbstractContainerMenu menu, int dataSlotIndex, int value) {\n\t\t// no menu data slots are mirrored into the entity\n\t}\n'''
    gb = gb.replace(marker, ins + marker)
gbase.write_text(gb)

print('Applied deterministic 26.1.2 migration pass 2')
