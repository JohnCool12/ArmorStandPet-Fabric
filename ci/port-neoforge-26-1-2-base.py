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
# The old MMD repository is offline and used to shadow CurseMaven lookups.
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

print('Prepared clean NeoForge 26.1.2 baseline (Java 25, MDG 2.0.144, NeoForge 26.1.2.94).')
