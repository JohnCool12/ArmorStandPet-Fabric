from pathlib import Path

root = Path("project/src/main/java/io/github/kyzderp/armorstandpet")


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Expected one {label} in {path}, found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


# HolderLookup.Provider does not exist in the 1.20.1 persistence signatures.
# Remove the parameter cleanly rather than leaving a trailing comma or an
# orphaned registryAccess assignment.
factory = root / "entity/StandFactory.java"
replace_once(
    factory,
    "public static PetArmorStandEntity fromData(ServerLevel world, PetData.StandData data, String owner, String typeKey,\n\t\t\t)",
    "public static PetArmorStandEntity fromData(ServerLevel world, PetData.StandData data, String owner, String typeKey)",
    "StandFactory.fromData provider parameter",
)

storage = root / "storage/PetStorage.java"
replace_once(
    storage,
    "\n\t\t = ASPetMod.getServer().registryAccess();\n",
    "\n",
    "orphaned registry-access assignment",
)
replace_once(
    storage,
    "PetArmorStandEntity stand = StandFactory.fromData(serverWorld, data.stand, owner, type.name(),\n\t\t\t\t);",
    "PetArmorStandEntity stand = StandFactory.fromData(serverWorld, data.stand, owner, type.name());",
    "StandFactory.fromData provider argument",
)

# Forge 1.20.1 exposes the cancellable RightClickBlock event itself rather than
# the later ForgeEventFactory convenience method. Post the same event directly
# so protection mods retain the opportunity to veto synthetic stand placement.
building = root / "hooks/BuildingCheck.java"
building.write_text("""/*******************************************************************************
 * ArmorStandPet - Forge port
 ******************************************************************************/
package io.github.kyzderp.armorstandpet.hooks;

import io.github.kyzderp.armorstandpet.util.Pos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.eventbus.api.Event;

/** Lets Forge protection mods veto a synthetic armor-stand placement check. */
public class BuildingCheck
{
    public boolean canPlaceArmorStand(ServerPlayer player, Pos loc)
    {
        BlockPos below = new BlockPos(loc.getBlockX(), loc.getBlockY() - 1, loc.getBlockZ());
        BlockHitResult hit = new BlockHitResult(loc.toVec3d(), Direction.UP, below, false);
        PlayerInteractEvent.RightClickBlock event = new PlayerInteractEvent.RightClickBlock(
                player, InteractionHand.MAIN_HAND, below, hit);
        MinecraftForge.EVENT_BUS.post(event);
        return !event.isCanceled()
                && event.getUseBlock() != Event.Result.DENY
                && event.getUseItem() != Event.Result.DENY;
    }
}
""", encoding="utf-8")

# ArmorStand has no dedicated static attribute builder in 1.20.1. The custom
# pet is still a LivingEntity subclass, so use the vanilla living baseline and
# add the attack-damage attribute required by owner-directed combat.
attributes = root / "forge/CommonModEvents.java"
replace_once(
    attributes,
    "import net.minecraft.world.entity.decoration.ArmorStand;",
    "import net.minecraft.world.entity.LivingEntity;",
    "ArmorStand attribute import",
)
replace_once(
    attributes,
    "ArmorStand.createAttributes()",
    "LivingEntity.createLivingAttributes()",
    "1.20.1 living attribute builder",
)

# Guard against the same removal/API bugs appearing elsewhere.
for path in root.rglob("*.java"):
    source = path.read_text(encoding="utf-8")
    if "HolderLookup.Provider" in source or ".registryAccess()" in source:
        raise SystemExit(f"Newer registry-provider API remained in {path}")
    if "\n\t\t = ASPetMod" in source:
        raise SystemExit(f"Orphaned assignment remained in {path}")

building_source = building.read_text(encoding="utf-8")
if "ForgeEventFactory.onRightClickBlock" in building_source:
    raise SystemExit("Unavailable ForgeEventFactory placement helper remained")
for marker in [
    "new PlayerInteractEvent.RightClickBlock",
    "MinecraftForge.EVENT_BUS.post(event)",
    "event.getUseBlock() != Event.Result.DENY",
    "event.getUseItem() != Event.Result.DENY",
]:
    if marker not in building_source:
        raise SystemExit(f"Protection-event bridge missing {marker!r}")

attribute_source = attributes.read_text(encoding="utf-8")
if "ArmorStand.createAttributes()" in attribute_source:
    raise SystemExit("Unavailable ArmorStand attribute builder remained")
if "LivingEntity.createLivingAttributes()" not in attribute_source:
    raise SystemExit("LivingEntity attribute builder was not installed")
if ".add(Attributes.ATTACK_DAMAGE, 1.0D)" not in attribute_source:
    raise SystemExit("Pet attack-damage attribute was lost")

print("Adapted persistence, protection events, and entity attributes to Forge 1.20.1")
