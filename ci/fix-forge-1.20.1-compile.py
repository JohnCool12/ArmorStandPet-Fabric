from pathlib import Path

root = Path("project/src/main/java/io/github/kyzderp/armorstandpet")


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Expected one {label} in {path}, found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


def replace_count(path: Path, old: str, new: str, expected: int, label: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != expected:
        raise SystemExit(f"Expected {expected} {label} occurrences in {path}, found {count}")
    path.write_text(source.replace(old, new), encoding="utf-8")


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

# Forge dispatches armor-stand clicks through EntityInteractSpecific before the
# generic EntityInteract event. Subscribe to both and send them through one
# unchanged setup path so sneak-right-click pet creation works reliably.
events = root / "forge/ForgeEventHandlers.java"
replace_once(
    events,
    "    @SubscribeEvent\n    public static void onEntityInteract(PlayerInteractEvent.EntityInteract event)\n    {\n        if (!(event.getEntity() instanceof ServerPlayer player))\n            return;\n        ActionResult result = PlayerActionListener.onUseEntity(\n                player, player.level(), event.getHand(), event.getTarget(), null);\n        apply(event, result);\n    }",
    "    @SubscribeEvent\n    public static void onEntityInteractSpecific(PlayerInteractEvent.EntityInteractSpecific event)\n    {\n        if (!(event.getEntity() instanceof ServerPlayer player))\n            return;\n        ActionResult result = PlayerActionListener.onUseEntity(\n                player, player.level(), event.getHand(), event.getTarget(), event.getLocalPos());\n        apply(event, result);\n    }\n\n    @SubscribeEvent\n    public static void onEntityInteract(PlayerInteractEvent.EntityInteract event)\n    {\n        if (!(event.getEntity() instanceof ServerPlayer player))\n            return;\n        ActionResult result = PlayerActionListener.onUseEntity(\n                player, player.level(), event.getHand(), event.getTarget(), null);\n        apply(event, result);\n    }",
    "specific armor-stand interaction bridge",
)

# Smooth movement without changing effective speed. The original code moved one
# full speed-sized step every three ticks. Keep the same planning and animation
# cadence, but split that distance into three one-tick substeps. This reduces
# visible position jumps while preserving /aspet speed and combat timing.
pet = root / "types/Pet.java"
replace_once(
    pet,
    "\t// Which stage of the walking animation is this armorstand in?\n\tprotected int walkStage;",
    "\t// Which stage of the walking animation is this armorstand in?\n\tprotected int walkStage;\n\n\tprivate static final double SMOOTH_STEP_SCALE = 1.0D / 3.0D;\n\tprivate int smoothStepPhase;",
    "smooth movement state",
)
replace_once(
    pet,
    "\tpublic abstract void takeStep();",
    "\t/** Preserves the original full movement step for compatibility. */\n\tpublic final void takeStep()\n\t{\n\t\tthis.takeStep(1.0D);\n\t}\n\n\t/** Moves one scaled portion of the pet's configured speed. */\n\tpublic abstract void takeStep(double distanceScale);\n\n\t/**\n\t * Executes one of three equal per-tick substeps. Walking poses still advance\n\t * only once per three substeps, matching the original animation cadence.\n\t */\n\tpublic final void takeSmoothStep()\n\t{\n\t\tif (this.smoothStepPhase == 0)\n\t\t\tthis.animateWalk();\n\t\tthis.takeStep(SMOOTH_STEP_SCALE);\n\t\tthis.smoothStepPhase = (this.smoothStepPhase + 1) % 3;\n\t}",
    "scaled movement API",
)

for type_name in ("NeedyChildPet", "DemonPet", "SillyWalkerPet", "DoormanPet"):
    type_path = root / f"types/{type_name}.java"
    replace_once(
        type_path,
        "\tpublic void takeStep()",
        "\tpublic void takeStep(double distanceScale)",
        f"{type_name} scaled takeStep signature",
    )

for type_name in ("NeedyChildPet", "DemonPet", "SillyWalkerPet"):
    type_path = root / f"types/{type_name}.java"
    replace_once(
        type_path,
        "Vec walk = standDirection.normalize().multiply(this.speed);",
        "Vec walk = standDirection.normalize().multiply(this.speed * distanceScale);",
        f"{type_name} scaled movement distance",
    )

walk_loc = root / "tasks/WalkLocTask.java"
replace_once(
    walk_loc,
    "\t\tthis.pet.animateWalk();\n\t\tthis.pet.takeStep();",
    "\t\tthis.pet.takeSmoothStep();",
    "WalkLocTask smooth substep",
)
replace_once(
    walk_loc,
    ")).runTaskLater(3);",
    ")).runTaskLater(1);",
    "WalkLocTask one-tick cadence",
)

walk_player = root / "tasks/WalkPlayerTask.java"
replace_once(
    walk_player,
    "\t\tthis.pet.animateWalk();\n\t\tthis.pet.takeStep();",
    "\t\tthis.pet.takeSmoothStep();",
    "WalkPlayerTask smooth substep",
)
replace_once(
    walk_player,
    ")).runTaskLater(3);",
    ")).runTaskLater(1);",
    "WalkPlayerTask one-tick cadence",
)

chase = root / "tasks/ChasePathTask.java"
replace_once(
    chase,
    "\t\tif (this.iters > 20)",
    "\t\tif (this.iters > 60)",
    "real-time-equivalent stuck threshold",
)
replace_once(
    chase,
    "\t\tthis.pet.animateWalk();\n\t\tthis.pet.takeStep();",
    "\t\tthis.pet.takeSmoothStep();",
    "ChasePathTask smooth substep",
)
replace_count(
    chase,
    ").runTaskLater(3);",
    ").runTaskLater(1);",
    2,
    "ChasePathTask one-tick cadence",
)

combat = root / "combat/OwnerAttackCombatController.java"
replace_once(
    combat,
    "\t// Normal WalkPlayerTask takes one speed-sized step every three ticks. Using\n\t// the same cadence here makes combat pursuit obey /aspet speed identically.\n\tprivate static final long MOVEMENT_STEP_INTERVAL_TICKS = 3L;",
    "\t// Movement is split into three one-tick substeps, preserving the original\n\t// total distance per three ticks while making pursuit visually smoother.\n\tprivate static final long MOVEMENT_STEP_INTERVAL_TICKS = 1L;",
    "combat smooth movement interval",
)
replace_once(
    combat,
    "\t\t\t\t\tpet.animateWalk();\n\t\t\t\t\tpet.takeStep();",
    "\t\t\t\t\tpet.takeSmoothStep();",
    "combat smooth substep",
)
replace_once(
    combat,
    "\t\t\t\t// takeStep() uses the pet's saved /aspet speed value. Matching the\n\t\t\t\t// normal follow task's three-tick interval keeps the actual travel\n\t\t\t\t// speed identical while combat still starts immediately.",
    "\t\t\t\t// takeSmoothStep() uses one third of the configured /aspet speed\n\t\t\t\t// every tick, preserving the original total travel speed.",
    "combat movement comment",
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

event_source = events.read_text(encoding="utf-8")
for marker in [
    "onEntityInteractSpecific(PlayerInteractEvent.EntityInteractSpecific event)",
    "event.getLocalPos()",
    "onEntityInteract(PlayerInteractEvent.EntityInteract event)",
    "PlayerActionListener.onUseEntity",
]:
    if marker not in event_source:
        raise SystemExit(f"Armor-stand interaction bridge missing {marker!r}")

pet_source = pet.read_text(encoding="utf-8")
for marker in [
    "SMOOTH_STEP_SCALE = 1.0D / 3.0D",
    "public final void takeSmoothStep()",
    "this.takeStep(SMOOTH_STEP_SCALE)",
    "this.animateWalk()",
]:
    if marker not in pet_source:
        raise SystemExit(f"Smooth movement core missing {marker!r}")

for path in (walk_loc, walk_player, chase, combat):
    source = path.read_text(encoding="utf-8")
    if "this.pet.animateWalk();\n\t\tthis.pet.takeStep();" in source:
        raise SystemExit(f"Legacy three-tick movement call remained in {path}")
    if "takeSmoothStep()" not in source:
        raise SystemExit(f"Smooth movement call missing from {path}")

if "MOVEMENT_STEP_INTERVAL_TICKS = 1L" not in combat.read_text(encoding="utf-8"):
    raise SystemExit("Combat movement is not running every tick")
if "if (this.iters > 60)" not in chase.read_text(encoding="utf-8"):
    raise SystemExit("Chase stuck timeout was not scaled for one-tick substeps")

print("Adapted Forge 1.20.1 APIs, interaction events, and smooth per-tick pet movement")
