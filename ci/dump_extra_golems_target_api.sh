#!/usr/bin/env bash
set -euo pipefail
out="target-api.txt"
: > "$out"
jarfile="$(find ~/.gradle/caches -type f \( -name 'minecraft-client-patched-26.1.2.95.jar' -o -name 'minecraft-merged-*.jar' -o -name '*26.1.2.95*.jar' \) | head -n1 || true)"
if [ -z "$jarfile" ]; then
  echo 'No patched Minecraft jar found in cache' > "$out"
  find ~/.gradle/caches -type f -name '*.jar' | grep -E 'minecraft|26\.1\.2' | head -100 >> "$out" || true
  exit 0
fi
{
  echo "JAR=$jarfile"
  echo '=== relevant class-name searches ==='
  jar tf "$jarfile" | grep -E 'commands/arguments/.*(Identifier|Resource|Key)|world/entity/projectile/.+(Snowball|Fireball|Arrow)|client/model/.+IronGolem|client/renderer/.+(RenderType|RenderStateShard|LightTexture)|client/gui/GuiGraphics' | sort || true
} >> "$out"
classes=(
  net.minecraft.world.level.Level
  net.minecraft.server.level.ServerLevel
  net.minecraft.world.entity.Entity
  net.minecraft.world.entity.LivingEntity
  net.minecraft.world.entity.Mob
  net.minecraft.world.entity.NeutralMob
  net.minecraft.world.entity.animal.golem.IronGolem
  net.minecraft.world.entity.animal.golem.SnowGolem
  net.minecraft.world.item.ItemStack
  net.minecraft.world.item.Item
  net.minecraft.world.SimpleContainer
  net.minecraft.world.inventory.ContainerListener
  net.minecraft.nbt.CompoundTag
  net.minecraft.nbt.ValueInput
  net.minecraft.nbt.ValueOutput
  net.minecraft.core.Registry
  net.minecraft.resources.ResourceKey
  net.minecraft.util.valueproviders.IntProvider
  net.minecraft.world.level.pathfinder.PathType
  net.minecraft.world.entity.npc.InventoryCarrier
  net.minecraft.world.item.crafting.Ingredient
  net.minecraft.nbt.TagParser
  net.minecraft.world.entity.EntityType
  net.minecraft.server.level.ServerPlayer
  net.minecraft.commands.CommandSourceStack
  net.minecraft.world.level.block.state.BlockBehaviour
  net.minecraft.world.item.context.UseOnContext
  net.minecraft.world.level.biome.Biome
  net.minecraft.world.level.storage.loot.LootTable
  net.minecraft.world.entity.projectile.arrow.AbstractArrow
  net.minecraft.world.entity.projectile.hurtingprojectile.SmallFireball
  net.minecraft.world.entity.projectile.throwableitemprojectile.Snowball
)
for c in "${classes[@]}"; do
  echo >> "$out"
  echo "===== $c =====" >> "$out"
  javap -classpath "$jarfile" -p "$c" >> "$out" 2>&1 || true
done
