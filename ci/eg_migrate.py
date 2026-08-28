#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "work").resolve()
SRC = ROOT / "src/main/java"


def replace_file(path: Path, replacements):
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
# Optional HUD integrations are restored only after core gameplay compiles cleanly.
s = s[:dep_start] + 'dependencies {\n}\n' + s[dep_end + 2:]
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

# ---- Keep optional HUD integrations out of the gameplay migration pass ----
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
for p in SRC.rglob('*.java'):
    text = p.read_text()
    text = text.replace('net.minecraft.ResourceLocationException', 'net.minecraft.IdentifierException')
    text = text.replace('ResourceLocationException', 'IdentifierException')
    text = text.replace('net.minecraft.resources.ResourceLocation', 'net.minecraft.resources.Identifier')
    text = re.sub(r'\bResourceLocation\b', 'Identifier', text)
    text = text.replace('net.minecraft.advancements.critereon', 'net.minecraft.advancements.criterion')
    text = text.replace('net.minecraft.world.ContainerListener', 'net.minecraft.world.inventory.ContainerListener')
    text = text.replace('net.minecraft.world.entity.animal.AbstractGolem', 'net.minecraft.world.entity.animal.golem.AbstractGolem')
    text = text.replace('net.minecraft.world.entity.animal.IronGolem', 'net.minecraft.world.entity.animal.golem.IronGolem')
    text = text.replace('MobSpawnType', 'EntitySpawnReason')
    p.write_text(text)

# ---- Removed NeoForge INBTSerializable: preserve the mod's explicit NBT contract ----
ibd = SRC / "com/mcmoddev/golems/data/behavior/data/IBehaviorData.java"
ibd.write_text('''package com.mcmoddev.golems.data.behavior.data;\n\nimport com.mcmoddev.golems.entity.IExtraGolem;\nimport net.minecraft.core.HolderLookup;\nimport net.minecraft.nbt.CompoundTag;\n\n/**\n * Per-golem behavior state. Kept as an explicit internal serialization contract\n * rather than depending on a loader serialization convenience interface.\n * @see com.mcmoddev.golems.data.behavior.Behavior#onAttachData(IExtraGolem)\n */\npublic interface IBehaviorData {\n    CompoundTag serializeNBT(HolderLookup.Provider provider);\n    void deserializeNBT(HolderLookup.Provider provider, CompoundTag tag);\n}\n''')

# ---- 26.1.2 Item interaction result API ----
guide = SRC / "com/mcmoddev/golems/item/GuideBookItem.java"
g = guide.read_text()
g = g.replace('import net.minecraft.world.InteractionResultHolder;\n', '')
g = g.replace('public InteractionResultHolder<ItemStack> use(Level worldIn, Player playerIn, InteractionHand handIn)',
              'public InteractionResult use(Level worldIn, Player playerIn, InteractionHand handIn)')
g = g.replace('return new InteractionResultHolder<>(InteractionResult.SUCCESS, itemstack);', 'return InteractionResult.SUCCESS;')
guide.write_text(g)

# ---- 26.1.2 spawn egg: vanilla SpawnEggItem + ENTITY_DATA component through Properties.spawnEgg ----
registry = SRC / "com/mcmoddev/golems/EGRegistry.java"
r = registry.read_text()
r = r.replace('import net.neoforged.neoforge.common.DeferredSpawnEggItem;', 'import net.minecraft.world.item.SpawnEggItem;')
r = r.replace('DeferredHolder<Item, DeferredSpawnEggItem>', 'DeferredHolder<Item, SpawnEggItem>')
r = re.sub(
    r'\(\) -> new DeferredSpawnEggItem\(EntityReg\.GOLEM,\s*0x[0-9A-Fa-f]+,\s*0x[0-9A-Fa-f]+,\s*new Item\.Properties\(\)\)',
    '() -> new SpawnEggItem(new Item.Properties().spawnEgg(EntityReg.GOLEM.get()))',
    r,
)
registry.write_text(r)

print('Applied deterministic 26.1.2 migration pass')
