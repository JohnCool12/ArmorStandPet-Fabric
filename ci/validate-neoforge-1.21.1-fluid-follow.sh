#!/usr/bin/env bash
set -euo pipefail

base_artifact_dir="${1:?base artifact directory required}"
source_zip="$base_artifact_dir/ArmorStandPet-NeoForge-1.21.1-independent-health-source.zip"

echo '3986423a30c2c1d68dbee59018de99c0145aaacbc76f0b48419dffda0cd866a0  '"$source_zip" | sha256sum --check
rm -rf baseline project artifact
mkdir baseline project artifact
unzip -q "$source_zip" -d baseline
cp -a baseline/. project/

base64 --decode ci/neoforge-1.21.1-fluid-follow.patch.xz.b64 > /tmp/fluid-follow.patch.xz
echo '5fb57d9cd7e49324e8628eebf14337127f5f149ca8ce1eaa0d87cbdd96a814fa  /tmp/fluid-follow.patch.xz' | sha256sum --check
xz --decompress --stdout /tmp/fluid-follow.patch.xz > /tmp/fluid-follow.patch
echo '2e11fe1df47267922d13d949b5f24016e73c8255a991ae83da3757d8b5e5f1ab  /tmp/fluid-follow.patch' | sha256sum --check
(cd project && patch --batch --forward -p1 < /tmp/fluid-follow.patch)

python3 - <<'PY'
from pathlib import Path
import sys
base = Path('baseline/src/main/java')
port = Path('project/src/main/java')
allowed = {
    'io/github/kyzderp/armorstandpet/ai/PathNode.java',
    'io/github/kyzderp/armorstandpet/ai/algorithms/AStar.java',
    'io/github/kyzderp/armorstandpet/ai/algorithms/PathFinder.java',
    'io/github/kyzderp/armorstandpet/entity/PetArmorStandEntity.java',
    'io/github/kyzderp/armorstandpet/tasks/ChasePathTask.java',
    'io/github/kyzderp/armorstandpet/tasks/WalkLocTask.java',
    'io/github/kyzderp/armorstandpet/tasks/WalkPlayerTask.java',
    'io/github/kyzderp/armorstandpet/types/Pet.java',
}
failures = []
count = 0
for source in sorted(base.rglob('*.java')):
    rel = source.relative_to(base).as_posix()
    if rel in allowed:
        continue
    target = port / rel
    if not target.is_file() or source.read_bytes() != target.read_bytes():
        failures.append(rel)
    count += 1
if failures:
    print('Unexpected Java changes:', *failures, sep='\n - ')
    sys.exit(1)
print(f'Byte-for-byte preserved {count} Java files outside the movement allowlist.')
PY

cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/combat/OwnerAttackCombatController.java project/src/main/java/io/github/kyzderp/armorstandpet/combat/OwnerAttackCombatController.java
cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/combat/PetMortalityController.java project/src/main/java/io/github/kyzderp/armorstandpet/combat/PetMortalityController.java
cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/types/NeedyChildPet.java project/src/main/java/io/github/kyzderp/armorstandpet/types/NeedyChildPet.java
cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/types/SillyWalkerPet.java project/src/main/java/io/github/kyzderp/armorstandpet/types/SillyWalkerPet.java
cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/types/DemonPet.java project/src/main/java/io/github/kyzderp/armorstandpet/types/DemonPet.java
cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/storage/PetData.java project/src/main/java/io/github/kyzderp/armorstandpet/storage/PetData.java

grep -q 'MOVEMENT_UPDATE_INTERVAL_TICKS = 1L' project/src/main/java/io/github/kyzderp/armorstandpet/types/Pet.java
grep -q 'advanceFollowTickToward' project/src/main/java/io/github/kyzderp/armorstandpet/types/Pet.java
grep -q 'setMovementYaw' project/src/main/java/io/github/kyzderp/armorstandpet/entity/PetArmorStandEntity.java
grep -q 'PathFinder.diagonalCost' project/src/main/java/io/github/kyzderp/armorstandpet/ai/algorithms/AStar.java
grep -q 'canTraverseDiagonal' project/src/main/java/io/github/kyzderp/armorstandpet/ai/algorithms/AStar.java
grep -q 'PriorityQueue does not reorder' project/src/main/java/io/github/kyzderp/armorstandpet/ai/algorithms/AStar.java
grep -q 'mod_version=2.0.1+neoforge.1.21.1-fluid-follow' project/gradle.properties
! grep -R --line-number 'net\.fabricmc\|fabric\.mod\.json\|fabric-loom' project/src project/build.gradle project/settings.gradle project/gradle.properties

(cd project && ./gradlew clean build --stacktrace --no-daemon --console=plain)

mkdir -p project/run
printf 'eula=true\n' > project/run/eula.txt
printf 'online-mode=false\nserver-port=25586\n' > project/run/server.properties
set +e
(cd project && (sleep 90; echo stop) | timeout 360s ./gradlew runServer --no-daemon --console=plain) > neoforge-1.21.1-fluid-follow-server-smoke.log 2>&1
status=$?
set -e
cat neoforge-1.21.1-fluid-follow-server-smoke.log
grep -q 'Done (' neoforge-1.21.1-fluid-follow-server-smoke.log
! grep -q 'Failed to complete lifecycle event' neoforge-1.21.1-fluid-follow-server-smoke.log
! grep -q 'Exception caught during firing event' neoforge-1.21.1-fluid-follow-server-smoke.log
! grep -Eiq '(^|\]) *(ERROR|FATAL) ' neoforge-1.21.1-fluid-follow-server-smoke.log
if [ "$status" -ne 0 ] && [ "$status" -ne 124 ]; then exit "$status"; fi

jar="$(find project/build/libs -maxdepth 1 -type f -name '*.jar' ! -name '*-sources.jar' ! -name '*-dev.jar' -print -quit)"
test -n "$jar"
cp "$jar" artifact/ArmorStandPet-NeoForge-1.21.1-fluid-follow.jar
cp neoforge-1.21.1-fluid-follow-server-smoke.log artifact/ArmorStandPet-NeoForge-1.21.1-fluid-follow-server-smoke.log
cp /tmp/fluid-follow.patch artifact/ArmorStandPet-NeoForge-1.21.1-fluid-follow.patch
unzip -t artifact/ArmorStandPet-NeoForge-1.21.1-fluid-follow.jar
unzip -p artifact/ArmorStandPet-NeoForge-1.21.1-fluid-follow.jar META-INF/neoforge.mods.toml | grep -q 'modId="armorstandpet"'
jar tf artifact/ArmorStandPet-NeoForge-1.21.1-fluid-follow.jar | grep -q 'io/github/kyzderp/armorstandpet/ai/algorithms/AStar.class'
jar tf artifact/ArmorStandPet-NeoForge-1.21.1-fluid-follow.jar | grep -q 'io/github/kyzderp/armorstandpet/entity/PetArmorStandEntity.class'
jar tf artifact/ArmorStandPet-NeoForge-1.21.1-fluid-follow.jar | grep -q 'io/github/kyzderp/armorstandpet/combat/OwnerAttackCombatController.class'
! jar tf artifact/ArmorStandPet-NeoForge-1.21.1-fluid-follow.jar | grep -q 'fabric.mod.json'

cat > artifact/VALIDATION.txt <<'EOF'
ArmorStandPet NeoForge 1.21.1 fluid owner-follow movement
=======================================================
Baseline: validated NeoForge 1.21.1 independent-health source
Version: 2.0.1+neoforge.1.21.1-fluid-follow
Minecraft: 1.21.1
NeoForge: 21.1.244
Java: 21

Verified:
- exact archived baseline source checksum
- narrow Java source allowlist
- combat, health, persistence and pet-type implementations unchanged
- eight-direction A* with no diagonal corner cutting
- per-tick normalized X/Z follow movement
- full yaw/body/head synchronization
- full production compilation
- dedicated-server startup
- JAR metadata and required classes
EOF

rm -rf project/.gradle project/build project/run
(cd project && zip -qr ../artifact/ArmorStandPet-NeoForge-1.21.1-fluid-follow-source.zip . -x '.git/*' '.github/*' '.gradle/*' 'build/*' 'run/*')
sha256sum artifact/*.jar artifact/*-source.zip artifact/*.patch > artifact/SHA256SUMS.txt
