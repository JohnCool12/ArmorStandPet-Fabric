#!/usr/bin/env bash
set -euo pipefail

BASE=/tmp/base-artifact/ArmorStandPet-NeoForge-1.21.1-uninterrupted-follow-source.zip
echo '22c4221bc3a220f0f357f8c0e721912738ede9c2ed733235618372d713e0b370  '"$BASE" | sha256sum --check

rm -rf project artifact
mkdir project artifact
unzip -q "$BASE" -d project

cat ci/neoforge6331-port.patch.xz.b64.part-* | base64 --decode > /tmp/neoforge6331-port.patch.xz
echo 'fe01befa9720e4f5d62a4920789f61649c6a16d7b8468426795ac7f433556083  /tmp/neoforge6331-port.patch.xz' | sha256sum --check
xz --decompress --stdout /tmp/neoforge6331-port.patch.xz > /tmp/neoforge6331-port.patch
(cd project && patch --batch --forward -p1 < /tmp/neoforge6331-port.patch)

grep -q '^minecraft_version=26.1.2$' project/gradle.properties
grep -q '^neo_version=26.1.2.95$' project/gradle.properties
grep -q '^mod_version=3.1.0+neoforge.26.1.2-fabric-6.33.1-parity$' project/gradle.properties
grep -q 'JavaLanguageVersion.of(25)' project/build.gradle
if grep -R --line-number -E 'net\.fabricmc|fabric\.api|fabric\.mod\.json|fabric-loom' project/src project/build.gradle project/settings.gradle project/gradle.properties; then
  echo 'Active Fabric production reference found' >&2
  exit 1
fi

cp /tmp/neoforge6331-port.patch artifact/ArmorStandPet-NeoForge-26.1.2-6.33.1-parity.patch

(cd project && ./gradlew clean build --stacktrace --no-daemon --console=plain)

mkdir -p project/run
printf 'eula=true\n' > project/run/eula.txt
printf 'online-mode=false\nserver-port=25591\n' > project/run/server.properties
set +e
(cd project && (sleep 100; echo stop) | timeout 420s ./gradlew runServer --no-daemon --console=plain) > artifact/ArmorStandPet-NeoForge-26.1.2-6.33.1-server-smoke.log 2>&1
status=$?
set -e
cat artifact/ArmorStandPet-NeoForge-26.1.2-6.33.1-server-smoke.log
grep -q 'Done (' artifact/ArmorStandPet-NeoForge-26.1.2-6.33.1-server-smoke.log
if grep -q 'Failed to complete lifecycle event' artifact/ArmorStandPet-NeoForge-26.1.2-6.33.1-server-smoke.log; then exit 1; fi
if grep -q 'Exception caught during firing event' artifact/ArmorStandPet-NeoForge-26.1.2-6.33.1-server-smoke.log; then exit 1; fi
if grep -Eiq '(^|\]) *(ERROR|FATAL) ' artifact/ArmorStandPet-NeoForge-26.1.2-6.33.1-server-smoke.log; then exit 1; fi
if [ "$status" -ne 0 ] && [ "$status" -ne 124 ]; then exit "$status"; fi

jar="$(find project/build/libs -maxdepth 1 -type f -name '*.jar' ! -name '*-sources.jar' ! -name '*-dev.jar' -print -quit)"
test -n "$jar"
cp "$jar" artifact/ArmorStandPet-NeoForge-26.1.2.95-6.33.1-parity.jar
unzip -t artifact/ArmorStandPet-NeoForge-26.1.2.95-6.33.1-parity.jar
unzip -p artifact/ArmorStandPet-NeoForge-26.1.2.95-6.33.1-parity.jar META-INF/neoforge.mods.toml | grep -q 'modId="armorstandpet"'
if jar tf artifact/ArmorStandPet-NeoForge-26.1.2.95-6.33.1-parity.jar | grep -q 'fabric.mod.json'; then exit 1; fi

for c in   io/github/kyzderp/armorstandpet/combat/OwnerAttackCombatController.class   io/github/kyzderp/armorstandpet/combat/PetBowCombatRuntime.class   io/github/kyzderp/armorstandpet/combat/PetSpecialRangedCombatRuntime.class   io/github/kyzderp/armorstandpet/swim/AquaticRuntime.class   io/github/kyzderp/armorstandpet/swim/ShoreExitRuntime.class   io/github/kyzderp/armorstandpet/normalcommands/TargetLockCommand.class   io/github/kyzderp/armorstandpet/listeners/PetPresentationFix.class   io/github/kyzderp/armorstandpet/listeners/PetDimensionStayFix.class
do
  jar tf artifact/ArmorStandPet-NeoForge-26.1.2.95-6.33.1-parity.jar | grep -q "$c"
done

cat > artifact/VALIDATION.txt <<'TXT'
ArmorStandPet NeoForge 26.1.2.95 — Fabric 6.33.1 gameplay parity port
=====================================================================
Target: Minecraft / NeoForge 26.1.2.95, Java 25
Gameplay target: Fabric 1.21.1 build 2.1.7.6.3.6.33.1-targetlock

Ported:
- /aspet targetlock on|off, OFF by default and persisted
- owner-directed melee/ranged target locking
- bow/trident/splash-potion combat and ammo modes
- combat movement smoothing and unlimited pursuit
- owner XP kill attribution
- /aspet swim, aquatic following and aquatic combat
- pet-driven surface swimming and 6.33 buoyancy profile
- shore-transition helpers
- land-parity aquatic follow handoff
- bounded A* / movement fixes
- look modes

NeoForge behavior retained:
- safe dimension transfer
- universal sitting dimension-stay
- universal presentation synchronization
- persistent pet chunk tickets
- ghost-safe persistence
- ditch-release behavior
- 26.1.2 runtime ABI corrections

Validation:
- exact NeoForge 1.21.1 baseline checksum verified
- deterministic migration patch checksum verified
- no Fabric Loader/API production references
- Java 25 production build succeeded
- dedicated NeoForge server reached Done
- no ERROR/FATAL lifecycle/event failure in smoke test
- expected gameplay and NeoForge lifecycle classes present
TXT

rm -rf project/.gradle project/build project/run
(cd project && zip -qr ../artifact/ArmorStandPet-NeoForge-26.1.2.95-6.33.1-parity-source.zip . -x '.git/*' '.github/*' '.gradle/*' 'build/*' 'run/*')
sha256sum   artifact/ArmorStandPet-NeoForge-26.1.2.95-6.33.1-parity.jar   artifact/ArmorStandPet-NeoForge-26.1.2.95-6.33.1-parity-source.zip   artifact/ArmorStandPet-NeoForge-26.1.2-6.33.1-parity.patch   artifact/ArmorStandPet-NeoForge-26.1.2-6.33.1-server-smoke.log   artifact/VALIDATION.txt > artifact/SHA256SUMS.txt
