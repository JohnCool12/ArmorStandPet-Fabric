#!/usr/bin/env bash
set -euo pipefail
out="target-api.txt"
: > "$out"

# Dump v3: pin to the exact NeoForge 26.1.2.95 patched Minecraft artifact.
# Do not scan arbitrary global caches: this runner also has unrelated 26.2 jars.
jarfile=""
while IFS= read -r candidate; do
  case "$candidate" in
    *-sources.jar|*-source.jar|*-javadoc.jar) continue ;;
  esac
  if jar tf "$candidate" 2>/dev/null | grep -qx 'net/minecraft/world/level/Level.class'; then
    jarfile="$candidate"
    break
  fi
done < <(
  {
    find ~/.gradle/caches -type f -path '*/net.neoforged/minecraft-client-patched/26.1.2.95/*' -name '*.jar' 2>/dev/null
    find target-mdk/build -type f -name '*.jar' 2>/dev/null
  } | sort -u
)

if [ -z "$jarfile" ]; then
  {
    echo 'No exact compiled Minecraft 26.1.2.95-containing jar found.'
    echo 'Exact-version candidates:'
    find ~/.gradle/caches -type f -path '*26.1.2.95*' -name '*.jar' | sort | head -300 || true
    echo 'target-mdk build jars:'
    find target-mdk/build -type f -name '*.jar' | sort | head -300 || true
    echo 'Artifact manifest:'
    find target-mdk/build -name 'nfrt_artifact_manifest.properties' -type f -print -exec cat {} \; || true
  } > "$out"
  exit 0
fi

{
  echo "JAR=$jarfile"
  echo '=== relevant class-name searches ==='
  jar tf "$jarfile" | grep -E 'commands/arguments/.*(Identifier|Resource|Key)|world/entity/projectile/.+(Snowball|Fireball|Arrow)|client/model/.+IronGolem|client/renderer/.+(RenderType|RenderStateShard|LightTexture|LightCoords)|client/gui/GuiGraphics|ContainerListener|SimpleContainer' | sort || true
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
  net.minecraft.world.Container
  net.minecraft.world.inventory.ContainerListener
  net.minecraft.world.inventory.AbstractContainerMenu
  net.minecraft.world.level.storage.ValueInput
  net.minecraft.world.level.storage.ValueOutput
  net.minecraft.nbt.CompoundTag
  net.minecraft.core.Registry
  net.minecraft.core.HolderLookup
  net.minecraft.resources.ResourceKey
  net.minecraft.resources.Identifier
  net.minecraft.util.valueproviders.IntProvider
  net.minecraft.world.level.pathfinder.PathType
  net.minecraft.world.entity.npc.InventoryCarrier
  net.minecraft.world.item.crafting.Ingredient
  net.minecraft.nbt.TagParser
  net.minecraft.world.entity.EntityType
  net.minecraft.world.entity.EntityReference
  net.minecraft.server.level.ServerPlayer
  net.minecraft.commands.CommandSourceStack
  net.minecraft.commands.arguments.IdentifierArgument
  net.minecraft.commands.arguments.ResourceKeyArgument
  net.minecraft.commands.arguments.ResourceOrIdArgument
  net.minecraft.world.level.block.state.BlockBehaviour
  net.minecraft.world.item.context.UseOnContext
  net.minecraft.world.level.biome.Biome
  net.minecraft.world.level.storage.loot.LootTable
  net.minecraft.world.entity.projectile.arrow.AbstractArrow
  net.minecraft.world.entity.projectile.hurtingprojectile.SmallFireball
  net.minecraft.world.entity.projectile.throwableitemprojectile.Snowball
  net.minecraft.client.gui.GuiGraphicsExtractor
  net.minecraft.client.model.animal.golem.IronGolemModel
  net.minecraft.client.renderer.entity.state.IronGolemRenderState
  net.minecraft.client.renderer.entity.IronGolemRenderer
  net.minecraft.client.renderer.entity.MobRenderer
  net.minecraft.client.renderer.entity.layers.RenderLayer
  net.minecraft.client.renderer.rendertype.RenderType
  net.minecraft.client.renderer.rendertype.RenderTypes
  net.minecraft.client.renderer.texture.DynamicTexture
  net.minecraft.client.renderer.texture.NativeImage
  net.minecraft.core.particles.SpellParticleOption
  net.minecraft.core.particles.ParticleTypes
)
for c in "${classes[@]}"; do
  echo >> "$out"
  echo "===== $c =====" >> "$out"
  javap -classpath "$jarfile" -p "$c" >> "$out" 2>&1 || true
done
