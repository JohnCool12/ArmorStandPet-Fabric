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

# Broad Mojang 26.1 naming/package migrations. Apply exception rename before Identifier rename.
java_root = root / 'src/main/java'
for f in java_root.rglob('*.java'):
    text = f.read_text()
    text = text.replace('net.minecraft.ResourceLocationException', 'net.minecraft.IdentifierException')
    text = text.replace('ResourceLocationException', 'IdentifierException')
    text = text.replace('net.minecraft.resources.ResourceLocation', 'net.minecraft.resources.Identifier')
    text = re.sub(r'\bResourceLocation\b', 'Identifier', text)
    text = text.replace('net.minecraft.advancements.critereon.MinMaxBounds', 'net.minecraft.advancements.criterion.MinMaxBounds')
    text = text.replace('net.minecraft.world.ContainerListener', 'net.minecraft.world.inventory.ContainerListener')
    text = text.replace('net.minecraft.world.entity.animal.AbstractGolem', 'net.minecraft.world.entity.animal.golem.AbstractGolem')
    text = text.replace('net.minecraft.world.entity.animal.IronGolem', 'net.minecraft.world.entity.animal.golem.IronGolem')
    text = text.replace('net.minecraft.world.entity.MobSpawnType', 'net.minecraft.world.entity.EntitySpawnReason')
    text = re.sub(r'\bMobSpawnType\b', 'EntitySpawnReason', text)
    text = text.replace('EntitySpawnReason.SPAWN_EGG', 'EntitySpawnReason.SPAWN_ITEM_USE')
    f.write_text(text)

# NeoForge removed INBTSerializable; keep the mod's exact behavior-data contract locally.
ibd = java_root / 'com/mcmoddev/golems/data/behavior/data/IBehaviorData.java'
text = ibd.read_text()
text = text.replace('import net.neoforged.neoforge.common.util.INBTSerializable;\n', '')
text = text.replace('public interface IBehaviorData extends INBTSerializable<CompoundTag> {', 'public interface IBehaviorData {')
if 'CompoundTag serializeNBT(HolderLookup.Provider provider);' not in text:
    text = text.replace('public interface IBehaviorData {', 'public interface IBehaviorData {\n\tCompoundTag serializeNBT(HolderLookup.Provider provider);\n\tvoid deserializeNBT(HolderLookup.Provider provider, CompoundTag tag);')
ibd.write_text(text)

print('Prepared NeoForge 26.1.2 baseline with first-pass Mojang/NeoForge API migrations.')
