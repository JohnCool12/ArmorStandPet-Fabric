#!/usr/bin/env bash
set -euo pipefail
artifact_dir="${1:?baseline artifact directory required}"
source_zip="$artifact_dir/ArmorStandPet-NeoForge-1.21.1-continuous-follow-source.zip"

echo '98f94fe0d349d73285d8dae19d8a56d7534cac29ec66e81df2e694760863bd93  '"$source_zip" | sha256sum --check
rm -rf baseline project artifact
mkdir baseline project artifact
unzip -q "$source_zip" -d baseline
cp -a baseline/. project/

base64 --decode ci/neoforge-1.21.1-uninterrupted-follow.patch.xz.b64 > /tmp/uninterrupted-follow.patch.xz
echo '5522ba4df2f25d1c3d3a2b485a2322618f9270ff131b9278bf571ebe0831350b  /tmp/uninterrupted-follow.patch.xz' | sha256sum --check
xz --decompress --stdout /tmp/uninterrupted-follow.patch.xz > /tmp/uninterrupted-follow.patch
echo 'f892b689452735596b2555336f0fc20e111595f3ec511e25ba5e1ff6eab9fb7c  /tmp/uninterrupted-follow.patch' | sha256sum --check
(cd project && patch --batch --forward -p1 < /tmp/uninterrupted-follow.patch)

python3 - <<'PY'
from pathlib import Path
import sys
base = Path('baseline/src/main/java')
port = Path('project/src/main/java')
allowed = {'io/github/kyzderp/armorstandpet/tasks/ChasePathTask.java'}
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
print(f'Byte-for-byte preserved {checked} Java files outside ChasePathTask.java.')
PY

cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/types/Pet.java project/src/main/java/io/github/kyzderp/armorstandpet/types/Pet.java
cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/ai/algorithms/AStar.java project/src/main/java/io/github/kyzderp/armorstandpet/ai/algorithms/AStar.java
cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/combat/OwnerAttackCombatController.java project/src/main/java/io/github/kyzderp/armorstandpet/combat/OwnerAttackCombatController.java
cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/combat/PetMortalityController.java project/src/main/java/io/github/kyzderp/armorstandpet/combat/PetMortalityController.java
cmp baseline/src/main/java/io/github/kyzderp/armorstandpet/storage/PetData.java project/src/main/java/io/github/kyzderp/armorstandpet/storage/PetData.java

grep -q 'mod_version=2.0.3+neoforge.1.21.1-uninterrupted-follow' project/gradle.properties
grep -q 'WAYPOINT_REACHED_EPSILON_SQUARED' project/src/main/java/io/github/kyzderp/armorstandpet/tasks/ChasePathTask.java
grep -q 'HORIZONTAL_DEAD_END_EPSILON_SQUARED' project/src/main/java/io/github/kyzderp/armorstandpet/tasks/ChasePathTask.java
grep -q 'MOVING_TARGET_REPATH_LOOKAHEAD_NODES = 2' project/src/main/java/io/github/kyzderp/armorstandpet/tasks/ChasePathTask.java
grep -q 'candidateDistanceSquared > this.distance' project/src/main/java/io/github/kyzderp/armorstandpet/tasks/ChasePathTask.java
grep -q 'standPos.setY(candidate.y)' project/src/main/java/io/github/kyzderp/armorstandpet/tasks/ChasePathTask.java
grep -q 'refresh only near its end' project/src/main/java/io/github/kyzderp/armorstandpet/tasks/ChasePathTask.java
! grep -R --line-number 'net\.fabricmc\|fabric\.mod\.json\|fabric-loom' project/src project/build.gradle project/settings.gradle project/gradle.properties

# Regression arithmetic: the previous comparison retained a waypoint exactly
# at the configured radius while the movement allowance became zero.
python3 - <<'PY'
threshold = 0.4
epsilon = 1.0e-7
at_boundary = threshold
assert not (at_boundary > threshold + epsilon)
remaining = max(0.0, at_boundary ** 0.5 - threshold ** 0.5)
assert remaining == 0.0
print('Exact-radius waypoint is consumed instead of entering the zero-movement dead zone.')
PY

(cd project && ./gradlew clean build --stacktrace --no-daemon --console=plain)

mkdir -p project/run
printf 'eula=true\n' > project/run/eula.txt
printf 'online-mode=false\nserver-port=25588\n' > project/run/server.properties
set +e
(cd project && (sleep 90; echo stop) | timeout 360s ./gradlew runServer --no-daemon --console=plain) > neoforge-1.21.1-uninterrupted-follow-server-smoke.log 2>&1
status=$?
set -e
cat neoforge-1.21.1-uninterrupted-follow-server-smoke.log
grep -q 'Done (' neoforge-1.21.1-uninterrupted-follow-server-smoke.log
! grep -q 'Failed to complete lifecycle event' neoforge-1.21.1-uninterrupted-follow-server-smoke.log
! grep -q 'Exception caught during firing event' neoforge-1.21.1-uninterrupted-follow-server-smoke.log
! grep -Eiq '(^|\]) *(ERROR|FATAL) ' neoforge-1.21.1-uninterrupted-follow-server-smoke.log
if [ "$status" -ne 0 ] && [ "$status" -ne 124 ]; then exit "$status"; fi

jar="$(find project/build/libs -maxdepth 1 -type f -name '*.jar' ! -name '*-sources.jar' ! -name '*-dev.jar' -print -quit)"
test -n "$jar"
cp "$jar" artifact/ArmorStandPet-NeoForge-1.21.1-uninterrupted-follow.jar
cp neoforge-1.21.1-uninterrupted-follow-server-smoke.log artifact/ArmorStandPet-NeoForge-1.21.1-uninterrupted-follow-server-smoke.log
cp /tmp/uninterrupted-follow.patch artifact/ArmorStandPet-NeoForge-1.21.1-uninterrupted-follow.patch
unzip -t artifact/ArmorStandPet-NeoForge-1.21.1-uninterrupted-follow.jar
unzip -p artifact/ArmorStandPet-NeoForge-1.21.1-uninterrupted-follow.jar META-INF/neoforge.mods.toml | grep -q 'modId="armorstandpet"'
jar tf artifact/ArmorStandPet-NeoForge-1.21.1-uninterrupted-follow.jar | grep -q 'io/github/kyzderp/armorstandpet/tasks/ChasePathTask.class'
jar tf artifact/ArmorStandPet-NeoForge-1.21.1-uninterrupted-follow.jar | grep -q 'io/github/kyzderp/armorstandpet/types/Pet.class'
! jar tf artifact/ArmorStandPet-NeoForge-1.21.1-uninterrupted-follow.jar | grep -q 'fabric.mod.json'

cat > artifact/VALIDATION.txt <<'TXT'
ArmorStandPet NeoForge 1.21.1 uninterrupted follow
================================================
Version: 2.0.3+neoforge.1.21.1-uninterrupted-follow
Baseline: validated 2.0.2 NeoForge 1.21.1 continuous-follow source
Minecraft: 1.21.1
NeoForge: 21.1.244
Java: 21

Verified:
- exact previous source checksum
- ChasePathTask.java is the only modified production Java file
- equality at the waypoint arrival radius is treated as reached
- same-X/Z vertical nodes cannot enter a horizontal zero-movement wait
- moving-owner A* refreshes occur only near the current route end
- speed, diagonal steering, yaw, animations, combat, health and persistence unchanged
- full NeoForge production compilation
- dedicated-server startup
- JAR metadata and required classes
TXT

rm -rf project/.gradle project/build project/run
(cd project && zip -qr ../artifact/ArmorStandPet-NeoForge-1.21.1-uninterrupted-follow-source.zip . -x '.git/*' '.github/*' '.gradle/*' 'build/*' 'run/*')
sha256sum artifact/*.jar artifact/*-source.zip artifact/*.patch > artifact/SHA256SUMS.txt
