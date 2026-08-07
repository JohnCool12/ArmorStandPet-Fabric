#!/usr/bin/env bash
set -euo pipefail
OUT="${1:-diagnostics}"
mkdir -p "$OUT"

find_jar() {
  local entry="$1"
  while IFS= read -r jar; do
    if jar tf "$jar" 2>/dev/null | grep -qx "$entry"; then
      printf '%s\n' "$jar"
      return 0
    fi
  done < <(find ~/.gradle/caches -type f -name '*.jar' | sort)
  return 1
}

MCJAR="$(find_jar 'net/minecraft/world/item/ItemStack.class')"
FABRICJAR="$(find_jar 'net/fabricmc/fabric/api/entity/event/v1/ServerEntityLevelChangeEvents.class')"
{
  echo "Minecraft: $MCJAR"
  echo "Fabric API: $FABRICJAR"
} > "$OUT/extra-jars.txt"

for cls in \
  net.minecraft.world.item.ItemStack \
  net.minecraft.world.item.component.ResolvableProfile \
  'net.minecraft.world.item.component.ResolvableProfile$Static' \
  'net.minecraft.world.item.component.ResolvableProfile$Partial' \
  'net.minecraft.core.HolderLookup$Provider' \
  net.minecraft.commands.CommandSourceStack \
  net.minecraft.server.players.PlayerList \
  net.minecraft.world.inventory.ContainerInput \
  net.minecraft.nbt.TagParser \
  net.minecraft.nbt.NbtOps \
  net.minecraft.resources.RegistryOps; do
  echo "===== $cls =====" >> "$OUT/javap-extra.txt"
  javap -classpath "$MCJAR" -protected "$cls" >> "$OUT/javap-extra.txt" 2>&1 || true
done

for cls in \
  net.fabricmc.fabric.api.entity.event.v1.ServerEntityLevelChangeEvents \
  'net.fabricmc.fabric.api.entity.event.v1.ServerEntityLevelChangeEvents$AfterPlayerChange' \
  net.fabricmc.fabric.api.permission.v1.PermissionContext \
  net.fabricmc.fabric.api.permission.v1.PermissionNode \
  net.fabricmc.fabric.api.permission.v1.PermissionPredicates; do
  echo "===== $cls =====" >> "$OUT/javap-extra.txt"
  javap -classpath "$FABRICJAR:$MCJAR" -protected "$cls" >> "$OUT/javap-extra.txt" 2>&1 || true
done
