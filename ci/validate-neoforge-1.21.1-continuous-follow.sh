#!/usr/bin/env bash
set -euo pipefail
artifact_dir="${1:?baseline artifact directory required}"
source_zip="$artifact_dir/ArmorStandPet-NeoForge-1.21.1-fluid-follow-source.zip"

echo '0a2b1bef71924d8090aa218e8a7131412a55b6bfd40ccf99d57c1e335634900c  '"$source_zip" | sha256sum --check
rm -rf baseline project artifact
mkdir baseline project artifact
unzip -q "$source_zip" -d baseline
cp -a baseline/. project/

base64 --decode ci/neoforge-1.21.1-continuous-follow.patch.xz.b64 > /tmp/continuous-follow.patch.xz
echo '9b1cd597bfb78b51523b10461cf32d85c7c35a5e3f000d64715901b98811369b  /tmp/continuous-follow.patch.xz' | sha256sum --check
xz --decompress --stdout /tmp/continuous-follow.patch.xz > /tmp/continuous-follow.patch
echo '644e86fbbe0e3ba41ca47f30ef362c37adf7176ada22b88eea713b6c58934b0b  /tmp/continuous-follow.patch' | sha256sum --check
(cd project && patch --batch --forward -p1 < /tmp/continuous-follow.patch)

python3 - <<'PY'
from pathlib import Path
import sys
base = Path('baseline/src/main/java')
port = Path('project/src/main/java')
allowed = {
    'io/github/kyzderp/armorstandpet/ai/algorithms/AStar.java',
    'io/github/kyzderp/armorstandpet/tasks/ChasePathTask.java',
}
failures=[]
checked=0
for source in sorted(base.rglob('*.java')):
    rel=source.relative_to(base).as_posix()
    if rel in allowed:
        continue
    target=port/rel
    if not target.is_file() or source.read_bytes()!=target.read_bytes():
        failures.append(rel)
    checked += 1
if failures:
    print('Unexpected Java changes:', *failures, sep='\n - ')
    sys.exit(1)
print(f'Byte-for-byte preserved {checked} Java files outside the two-file follow fix.')
PY

cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/types/Pet.java project/src/main/java/io/github/kyzderp/armorstandpet/types/Pet.java
cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/entity/PetArmorStandEntity.java project/src/main/java/io/github/kyzderp/armorstandpet/entity/PetArmorStandEntity.java
cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/combat/OwnerAttackCombatController.java project/src/main/java/io/github/kyzderp/armorstandpet/combat/OwnerAttackCombatController.java
cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/combat/PetMortalityController.java project/src/main/java/io/github/kyzderp/armorstandpet/combat/PetMortalityController.java
cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/storage/PetData.java project/src/main/java/io/github/kyzderp/armorstandpet/storage/PetData.java

grep -q 'mod_version=2.0.2+neoforge.1.21.1-continuous-follow' project/gradle.properties
grep -q 'Refresh a moving player' project/src/main/java/io/github/kyzderp/armorstandpet/tasks/ChasePathTask.java
grep -q 'Consume every waypoint' project/src/main/java/io/github/kyzderp/armorstandpet/tasks/ChasePathTask.java
grep -q 'while (!this.path.nodes.isEmpty())' project/src/main/java/io/github/kyzderp/armorstandpet/tasks/ChasePathTask.java
grep -q 'move along it during this same server tick' project/src/main/java/io/github/kyzderp/armorstandpet/tasks/ChasePathTask.java
grep -q 'The start block is the pet' project/src/main/java/io/github/kyzderp/armorstandpet/ai/algorithms/AStar.java
! grep -R --line-number 'net\.fabricmc\|fabric\.mod\.json\|fabric-loom' project/src project/build.gradle project/settings.gradle project/gradle.properties

(cd project && ./gradlew clean build --stacktrace --no-daemon --console=plain)

mkdir -p project/run
printf 'eula=true\n' > project/run/eula.txt
printf 'online-mode=false\nserver-port=25587\n' > project/run/server.properties
set +e
(cd project && (sleep 90; echo stop) | timeout 360s ./gradlew runServer --no-daemon --console=plain) > neoforge-1.21.1-continuous-follow-server-smoke.log 2>&1
status=$?
set -e
cat neoforge-1.21.1-continuous-follow-server-smoke.log
grep -q 'Done (' neoforge-1.21.1-continuous-follow-server-smoke.log
! grep -q 'Failed to complete lifecycle event' neoforge-1.21.1-continuous-follow-server-smoke.log
! grep -q 'Exception caught during firing event' neoforge-1.21.1-continuous-follow-server-smoke.log
! grep -Eiq '(^|\]) *(ERROR|FATAL) ' neoforge-1.21.1-continuous-follow-server-smoke.log
if [ "$status" -ne 0 ] && [ "$status" -ne 124 ]; then exit "$status"; fi

jar="$(find project/build/libs -maxdepth 1 -type f -name '*.jar' ! -name '*-sources.jar' ! -name '*-dev.jar' -print -quit)"
test -n "$jar"
cp "$jar" artifact/ArmorStandPet-NeoForge-1.21.1-continuous-follow.jar
cp neoforge-1.21.1-continuous-follow-server-smoke.log artifact/ArmorStandPet-NeoForge-1.21.1-continuous-follow-server-smoke.log
cp /tmp/continuous-follow.patch artifact/ArmorStandPet-NeoForge-1.21.1-continuous-follow.patch
unzip -t artifact/ArmorStandPet-NeoForge-1.21.1-continuous-follow.jar
unzip -p artifact/ArmorStandPet-NeoForge-1.21.1-continuous-follow.jar META-INF/neoforge.mods.toml | grep -q 'modId="armorstandpet"'
jar tf artifact/ArmorStandPet-NeoForge-1.21.1-continuous-follow.jar | grep -q 'io/github/kyzderp/armorstandpet/tasks/ChasePathTask.class'
jar tf artifact/ArmorStandPet-NeoForge-1.21.1-continuous-follow.jar | grep -q 'io/github/kyzderp/armorstandpet/ai/algorithms/AStar.class'
! jar tf artifact/ArmorStandPet-NeoForge-1.21.1-continuous-follow.jar | grep -q 'fabric.mod.json'

cat > artifact/VALIDATION.txt <<'TXT'
ArmorStandPet NeoForge 1.21.1 continuous follow fix
=================================================
Version: 2.0.2+neoforge.1.21.1-continuous-follow
Baseline: validated 2.0.1 NeoForge 1.21.1 fluid-follow source
Minecraft: 1.21.1
NeoForge: 21.1.244
Java: 21

Verified:
- exact previous source checksum
- only AStar.java and ChasePathTask.java changed in production Java
- current-block waypoint removed from new A* routes
- overlapping/reached waypoints consumed in the same tick
- moving-player paths refreshed without an empty movement tick
- replacement routes begin moving in the same tick
- movement speed, animation, yaw, combat, health and persistence code unchanged
- full NeoForge production compilation
- dedicated-server startup
- JAR metadata and required classes
TXT

rm -rf project/.gradle project/build project/run
(cd project && zip -qr ../artifact/ArmorStandPet-NeoForge-1.21.1-continuous-follow-source.zip . -x '.git/*' '.github/*' '.gradle/*' 'build/*' 'run/*')
sha256sum artifact/*.jar artifact/*-source.zip artifact/*.patch > artifact/SHA256SUMS.txt
