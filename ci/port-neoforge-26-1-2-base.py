from pathlib import Path
import re

root = Path('project')

build = root / 'build.gradle'
s = build.read_text()
s = s.replace("id 'net.neoforged.moddev' version '2.0.107'", "id 'net.neoforged.moddev' version '2.0.144'")
s = s.replace('java.toolchain.languageVersion = JavaLanguageVersion.of(21)', 'java.toolchain.languageVersion = JavaLanguageVersion.of(25)')
s = re.sub(r'\n\s*parchment \{.*?\n\s*\}\n', '\n', s, flags=re.S)
s = s.replace('implementation "curse.maven:the-one-probe-${project.top_proj}:${project.top_file}"', 'compileOnly "curse.maven:the-one-probe-${project.top_proj}:${project.top_file}"')
s = s.replace('implementation "curse.maven:jade-${project.jade_proj}:${project.jade_file}"', 'compileOnly "curse.maven:jade-${project.jade_proj}:${project.jade_file}"')
s = re.sub(r'\n\s*maven \{\s*\n\s*name "MMD"\s*\n\s*url "https://maven\.mcmoddev\.com/"\s*\n\s*\}\s*', '\n', s)
# Give migration runs the full error set instead of javac's default first 100.
if '-Xmaxerrs' not in s:
    s += "\n\ntasks.withType(JavaCompile).configureEach {\n    options.compilerArgs += ['-Xmaxerrs', '1000']\n}\n"
build.write_text(s)

props = root / 'gradle.properties'
p = props.read_text()
p = re.sub(r'^minecraft_version=.*$', 'minecraft_version=26.1.2', p, flags=re.M)
p = re.sub(r'^minecraft_version_range=.*$', 'minecraft_version_range=[26.1.2]', p, flags=re.M)
p = re.sub(r'^neo_version=.*$', 'neo_version=26.1.2.94', p, flags=re.M)
p = re.sub(r'^mod_version=.*$', 'mod_version=26.1.2.0', p, flags=re.M)
p = re.sub(r'^jade_file=.*$', 'jade_file=8651070', p, flags=re.M)
p = re.sub(r'^parchment_minecraft_version=.*\n?', '', p, flags=re.M)
p = re.sub(r'^parchment_mappings_version=.*\n?', '', p, flags=re.M)
props.write_text(p)

wrapper = root / 'gradle/wrapper/gradle-wrapper.properties'
w = wrapper.read_text()
w = re.sub(r'gradle-[0-9.]+-bin\.zip', 'gradle-9.5.1-bin.zip', w)
wrapper.write_text(w)

tmpl = root / 'src/main/templates/META-INF/neoforge.mods.toml'
t = tmpl.read_text().replace('versionRange="[15.0.0,)"', 'versionRange="[26.0.0,)"')
tmpl.write_text(t)

java_root = root / 'src/main/java'
for f in java_root.rglob('*.java'):
    text = f.read_text()
    # Mojang 26.1 naming/package moves.
    text = text.replace('net.minecraft.ResourceLocationException', 'net.minecraft.IdentifierException')
    text = text.replace('ResourceLocationException', 'IdentifierException')
    text = text.replace('net.minecraft.resources.ResourceLocation', 'net.minecraft.resources.Identifier')
    text = re.sub(r'\bResourceLocation\b', 'Identifier', text)
    text = text.replace('net.minecraft.advancements.critereon.MinMaxBounds', 'net.minecraft.advancements.criterion.MinMaxBounds')
    text = text.replace('net.minecraft.world.ContainerListener', 'net.minecraft.world.inventory.ContainerListener')
    text = text.replace('net.minecraft.world.entity.animal.AbstractGolem', 'net.minecraft.world.entity.animal.golem.AbstractGolem')
    text = text.replace('net.minecraft.world.entity.animal.IronGolem', 'net.minecraft.world.entity.animal.golem.IronGolem')
    text = text.replace('net.minecraft.world.entity.animal.SnowGolem', 'net.minecraft.world.entity.animal.golem.SnowGolem')
    text = text.replace('net.minecraft.world.entity.npc.AbstractVillager', 'net.minecraft.world.entity.npc.villager.AbstractVillager')
    text = text.replace('net.minecraft.world.entity.npc.Villager', 'net.minecraft.world.entity.npc.villager.Villager')
    text = text.replace('net.minecraft.world.entity.projectile.AbstractArrow', 'net.minecraft.world.entity.projectile.arrow.AbstractArrow')
    text = text.replace('net.minecraft.world.entity.projectile.SmallFireball', 'net.minecraft.world.entity.projectile.hurtingprojectile.SmallFireball')
    text = text.replace('net.minecraft.world.entity.projectile.Snowball', 'net.minecraft.world.entity.projectile.throwableitemprojectile.Snowball')
    text = text.replace('net.minecraft.world.entity.MobSpawnType', 'net.minecraft.world.entity.EntitySpawnReason')
    text = re.sub(r'\bMobSpawnType\b', 'EntitySpawnReason', text)
    text = text.replace('EntitySpawnReason.SPAWN_EGG', 'EntitySpawnReason.SPAWN_ITEM_USE')
    text = text.replace('net.minecraft.Util', 'net.minecraft.util.Util')
    text = text.replace('net.minecraft.commands.arguments.ResourceLocationArgument', 'net.minecraft.commands.arguments.IdentifierArgument')
    text = re.sub(r'\bResourceLocationArgument\b', 'IdentifierArgument', text)
    text = text.replace('FMLEnvironment.dist', 'FMLEnvironment.getDist()')

    # Straightforward method renames.
    text = text.replace('.registryOrThrow(', '.lookupOrThrow(')
    text = text.replace('.isInWaterRainOrBubble()', '.isInWaterOrRain()')
    text = text.replace('.isDay()', '.isBrightOutside()')
    text = text.replace('.isNight()', '.isDarkOutside()')
    text = text.replace('PathType.DAMAGE_FIRE', 'PathType.FIRE')
    text = text.replace('PathType.DANGER_FIRE', 'PathType.FIRE_IN_NEIGHBOR')
    text = text.replace('IdentifierArgument.getId(', 'IdentifierArgument.getId(')

    # CompoundTag typed contains/getters became Optional-returning APIs.
    text = re.sub(r'\.contains\(([^,\n]+),\s*Tag\.TAG_[A-Z_]+\)', r'.contains(\1)', text)
    # Specific persisted fields in this mod are byte/string values.
    text = text.replace('tag.getByte(KEY_VARIANT)', 'tag.getByte(KEY_VARIANT).orElse((byte) 0)')
    text = text.replace('pCompound.getString(KEY_GOLEM_ID)', 'pCompound.getString(KEY_GOLEM_ID).orElse("")')
    text = text.replace('pCompound.getString("Material")', 'pCompound.getString("Material").orElse("")')
    f.write_text(text)

# NeoForge removed INBTSerializable; keep the mod's exact behavior-data contract locally.
ibd = java_root / 'com/mcmoddev/golems/data/behavior/data/IBehaviorData.java'
text = ibd.read_text()
text = text.replace('import net.neoforged.neoforge.common.util.INBTSerializable;\n', '')
if 'import net.minecraft.core.HolderLookup;' not in text:
    text = text.replace('package com.mcmoddev.golems.data.behavior.data;\n', 'package com.mcmoddev.golems.data.behavior.data;\n\nimport net.minecraft.core.HolderLookup;\n')
text = text.replace('public interface IBehaviorData extends INBTSerializable<CompoundTag> {', 'public interface IBehaviorData {')
if 'CompoundTag serializeNBT(HolderLookup.Provider provider);' not in text:
    text = text.replace('public interface IBehaviorData {', 'public interface IBehaviorData {\n\tCompoundTag serializeNBT(HolderLookup.Provider provider);\n\tvoid deserializeNBT(HolderLookup.Provider provider, CompoundTag tag);')
ibd.write_text(text)

# Spawn eggs are vanilla items again in 26.1; the entity type lives in Item.Properties.
egreg = java_root / 'com/mcmoddev/golems/EGRegistry.java'
text = egreg.read_text()
text = text.replace('import net.neoforged.neoforge.common.DeferredSpawnEggItem;\n', 'import net.minecraft.world.item.SpawnEggItem;\n')
text = text.replace('DeferredHolder<Item, DeferredSpawnEggItem> GOLEM_SPAWN_EGG', 'DeferredHolder<Item, SpawnEggItem> GOLEM_SPAWN_EGG')
text = text.replace('new DeferredSpawnEggItem(EntityReg.GOLEM, 0x9B9B9B, 0x4A7D2C, new Item.Properties())', 'new SpawnEggItem(new Item.Properties().spawnEgg(EntityReg.GOLEM.get()))')
egreg.write_text(text)

# Item.use now returns InteractionResult directly; unchanged stack is implicit.
guide = java_root / 'com/mcmoddev/golems/item/GuideBookItem.java'
text = guide.read_text()
text = text.replace('import net.minecraft.world.InteractionResultHolder;\n', '')
text = text.replace('public InteractionResultHolder<ItemStack> use(Level worldIn, Player playerIn, InteractionHand handIn)', 'public InteractionResult use(Level worldIn, Player playerIn, InteractionHand handIn)')
text = text.replace('return new InteractionResultHolder<>(InteractionResult.SUCCESS, itemstack);', 'return InteractionResult.SUCCESS;')
guide.write_text(text)

# Command identifiers were renamed but keep the same command grammar.
cmd = java_root / 'com/mcmoddev/golems/network/SummonGolemCommand.java'
text = cmd.read_text().replace('IdentifierArgument.id()', 'IdentifierArgument.id()')
cmd.write_text(text)

print('Prepared NeoForge 26.1.2 baseline with second-pass common API migrations.')
