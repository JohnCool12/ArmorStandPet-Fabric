from pathlib import Path

root = Path('project')
build = root / 'build.gradle'
modjson = root / 'src/main/resources/fabric.mod.json'
testjava = root / 'src/main/java/com/mcmoddev/golems/test/BedrockNaturalAiGameTest.java'
build_backup = root / 'build.gradle.gametest-backup'
mod_backup = root / 'src/main/resources/fabric.mod.json.gametest-backup'

if not build_backup.exists() or not mod_backup.exists():
    raise SystemExit('Missing GameTest backup files')
build.write_text(build_backup.read_text())
modjson.write_text(mod_backup.read_text())
build_backup.unlink()
mod_backup.unlink()
if testjava.exists():
    testjava.unlink()
try:
    testjava.parent.rmdir()
except OSError:
    pass
print('Removed temporary Bedrock AI GameTest harness; production sources restored.')
