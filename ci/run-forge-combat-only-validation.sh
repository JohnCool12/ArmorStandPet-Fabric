#!/usr/bin/env bash
set -euo pipefail

(cd /tmp/exact-source && sha256sum --check armorstandpet-independent-1.21.1-source.tar.gz.sha256)
mkdir project
tar -xzf /tmp/exact-source/armorstandpet-independent-1.21.1-source.tar.gz -C project

cat ci/forge-port-script.b64.part-* | base64 --decode > /tmp/port-to-forge-1.20.1.py
python3 - <<'PY'
from pathlib import Path
path = Path('/tmp/port-to-forge-1.20.1.py')
source = path.read_text(encoding='utf-8')
source = source.replace('return ItemStackEMPTY;', 'return ItemStack.EMPTY;')
source = source.replace(
    "t = t.replace('\\n,\\t\\tHolderLookup.Provider registries = ASPetMod.getServer().registryAccess();\\n', '\\n')",
    "t = t.replace('\\n\\t\\tHolderLookup.Provider registries = ASPetMod.getServer().registryAccess();\\n', '\\n')",
)
path.write_text(source, encoding='utf-8')
PY
echo 'a73ae11aaac1ce330e459516c4371e3d06694c2bbf039c663cf3615d6c6615c0  /tmp/port-to-forge-1.20.1.py' | sha256sum --check
python3 /tmp/port-to-forge-1.20.1.py
python3 ci/fix-forge-1.20.1-compile.py

base64 --decode ci/forge-combat-only-smoothing.patch.xz.b64 > /tmp/combat-only.patch.xz
echo '32ad6179037ff694ef869b48d371eb519ad6245c0d01905d679495fde8f18051  /tmp/combat-only.patch.xz' | sha256sum --check
xz --decompress --stdout /tmp/combat-only.patch.xz > /tmp/combat-only.patch
(cd project && patch --batch --forward -p1 < /tmp/combat-only.patch)

src=project/src/main/java/io/github/kyzderp/armorstandpet
combat="$src/combat/OwnerAttackCombatController.java"
pet="$src/types/Pet.java"
grep -q 'LEGACY_MOVEMENT_INTERVAL_TICKS = 3.0D' "$combat"
grep -q 'WALK_ANIMATION_BLEND_TICKS = 3' "$combat"
grep -q 'GRAVITY_ACCELERATION_PER_TICK = 0.08D' "$combat"
grep -q 'MAX_FALL_SPEED_PER_TICK = 0.50D' "$combat"
grep -q 'ATTACK_APPROACH_DISTANCE = 1.75D' "$combat"
grep -q 'MAX_YAW_CHANGE_PER_TICK = 30.0F' "$combat"
grep -q 'moveCombatOneTick' "$combat"
grep -q 'resolveCombatTerrain' "$combat"
grep -q 'advanceCombatWalkAnimation' "$combat"
! grep -q 'nextMovementTick' "$combat"
grep -q 'public double getSpeed()' "$pet"

cd project
echo '2f7a71169121931eefc2840be37d4e692920e0a3caf334e3f3b50231ceec6bd0  src/main/java/io/github/kyzderp/armorstandpet/tasks/WalkPlayerTask.java' | sha256sum --check
echo '95e3bbfcc3efc4c5fc9593794a13b3d7d33f9c4d08215ff714aaa7def38dedc0  src/main/java/io/github/kyzderp/armorstandpet/tasks/WalkLocTask.java' | sha256sum --check
echo '0a2e54bf1dea473377222c6b11fcd69ccc824f92b623057980609e6a620c6cbe  src/main/java/io/github/kyzderp/armorstandpet/tasks/ChasePathTask.java' | sha256sum --check
echo 'd53e039367b14dc38a30e670c9a724ef528dd1beaa16edbd4c6d6a1251196e67  src/main/java/io/github/kyzderp/armorstandpet/types/NeedyChildPet.java' | sha256sum --check
echo '71954d69bdc1b4215281284376d95ea9d2b6033394b6129ae5f27909a91f349a  src/main/java/io/github/kyzderp/armorstandpet/types/SillyWalkerPet.java' | sha256sum --check
echo 'c47bcecd2bd3a4aa9e1a25f6faf3f0ac2ff1dc1191ad7468be72e461307879f6  src/main/java/io/github/kyzderp/armorstandpet/types/DemonPet.java' | sha256sum --check
grep -q 'PlayerInteractEvent.EntityInteractSpecific event' src/main/java/io/github/kyzderp/armorstandpet/forge/ForgeEventHandlers.java
grep -q 'public float health' src/main/java/io/github/kyzderp/armorstandpet/types/Pet.java
grep -q 'pet.health - appliedDamage' src/main/java/io/github/kyzderp/armorstandpet/combat/PetMortalityController.java
! grep -R 'net.fabricmc' src
! grep -q 'shadowRadius' src/main/java/io/github/kyzderp/armorstandpet/client/PetArmorStandRenderer.java
grep -q 'mod_version=2.0.1+forge.1.20.1-combat-smooth' gradle.properties
cd ..

curl --fail --location --retry 3 -o /tmp/forge-mdk.zip https://maven.minecraftforge.net/net/minecraftforge/forge/1.20.1-47.4.10/forge-1.20.1-47.4.10-mdk.zip
unzip -q /tmp/forge-mdk.zip -d /tmp/forge-mdk
cp /tmp/forge-mdk/gradlew project/
cp /tmp/forge-mdk/gradlew.bat project/
rm -rf project/gradle
cp -a /tmp/forge-mdk/gradle project/
chmod +x project/gradlew

(cd project && ./gradlew clean build --stacktrace --no-daemon --console=plain)

mkdir -p project/run
printf 'eula=true\n' > project/run/eula.txt
printf 'online-mode=false\nserver-port=25582\n' > project/run/server.properties
set +e
(cd project && (sleep 60; echo stop) | timeout 180s ./gradlew runServer --no-daemon --console=plain) > forge-combat-server-smoke.log 2>&1
status=$?
set -e
cat forge-combat-server-smoke.log
grep -q 'Done (' forge-combat-server-smoke.log
! grep -q 'Failed to complete lifecycle event' forge-combat-server-smoke.log
! grep -q 'Exception caught during firing event' forge-combat-server-smoke.log
! grep -Eiq '(^|\]) *(ERROR|FATAL) ' forge-combat-server-smoke.log
if [ "$status" -ne 0 ] && [ "$status" -ne 124 ]; then exit "$status"; fi

mkdir artifact
jar="$(find project/build/libs -maxdepth 1 -type f -name '*.jar' ! -name '*-sources.jar' ! -name '*-dev.jar' -print -quit)"
test -n "$jar"
cp "$jar" artifact/ArmorStandPet-Forge-1.20.1-combat-only-smoothing.jar
cp forge-combat-server-smoke.log artifact/
unzip -t artifact/ArmorStandPet-Forge-1.20.1-combat-only-smoothing.jar
unzip -p artifact/ArmorStandPet-Forge-1.20.1-combat-only-smoothing.jar META-INF/mods.toml | grep -q 'modId="armorstandpet"'
javap -classpath artifact/ArmorStandPet-Forge-1.20.1-combat-only-smoothing.jar -p -c io.github.kyzderp.armorstandpet.combat.OwnerAttackCombatController | tee artifact/OwnerAttackCombatController.javap.txt
grep -q 'moveCombatOneTick' artifact/OwnerAttackCombatController.javap.txt
grep -q 'resolveCombatTerrain' artifact/OwnerAttackCombatController.javap.txt
grep -q 'advanceCombatWalkAnimation' artifact/OwnerAttackCombatController.javap.txt
javap -classpath artifact/ArmorStandPet-Forge-1.20.1-combat-only-smoothing.jar -p -c io.github.kyzderp.armorstandpet.types.Pet | tee artifact/Pet.javap.txt
grep -q 'double getSpeed' artifact/Pet.javap.txt
grep -q 'float health' artifact/Pet.javap.txt
rm -rf project/.gradle project/build project/run
(cd project && zip -qr ../artifact/ArmorStandPet-Forge-1.20.1-combat-only-smoothing-source.zip . -x '.git/*' '.github/*' '.gradle/*' 'build/*' 'run/*')
sha256sum artifact/*.jar artifact/*-source.zip > artifact/SHA256SUMS.txt
