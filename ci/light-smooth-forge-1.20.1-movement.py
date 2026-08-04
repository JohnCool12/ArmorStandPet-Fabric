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


# Lightweight movement refinement:
# - keep the original face -> animate -> takeStep order and direction math
# - update that complete pair every two ticks instead of every three
# - scale each step to 2/3 distance, preserving configured travel speed
# - send entity tracking updates every tick so position and pose changes arrive
#   together without adding a second movement state machine
pet = root / "types/Pet.java"
replace_once(
    pet,
    "\t// Which stage of the walking animation is this armorstand in?\n\tprotected int walkStage;",
    "\t// Which stage of the walking animation is this armorstand in?\n\tprotected int walkStage;\n\n\t// Two-tick updates at two-thirds distance preserve the original speed.\n\tprotected static final double LIGHT_SMOOTH_STEP_SCALE = 2.0D / 3.0D;",
    "light smoothing scale",
)

for type_name in ("NeedyChildPet", "DemonPet", "SillyWalkerPet"):
    type_path = root / f"types/{type_name}.java"
    replace_once(
        type_path,
        "Vec walk = standDirection.normalize().multiply(this.speed);",
        "Vec walk = standDirection.normalize().multiply(this.speed * LIGHT_SMOOTH_STEP_SCALE);",
        f"{type_name} two-tick distance scale",
    )

walk_loc = root / "tasks/WalkLocTask.java"
replace_once(
    walk_loc,
    ")).runTaskLater(3);",
    ")).runTaskLater(2);",
    "WalkLocTask two-tick cadence",
)

walk_player = root / "tasks/WalkPlayerTask.java"
replace_once(
    walk_player,
    ")).runTaskLater(3);",
    ")).runTaskLater(2);",
    "WalkPlayerTask two-tick cadence",
)

chase = root / "tasks/ChasePathTask.java"
replace_once(
    chase,
    "\t\tif (this.iters > 20)",
    "\t\tif (this.iters > 30)",
    "real-time-equivalent chase timeout",
)
replace_count(
    chase,
    "runTaskLater(3)",
    "runTaskLater(2)",
    2,
    "ChasePathTask two-tick cadence",
)

combat = root / "combat/OwnerAttackCombatController.java"
replace_once(
    combat,
    "\t// Normal WalkPlayerTask takes one speed-sized step every three ticks. Using\n\t// the same cadence here makes combat pursuit obey /aspet speed identically.\n\tprivate static final long MOVEMENT_STEP_INTERVAL_TICKS = 3L;",
    "\t// Movement and walking animation update together every two ticks. Each\n\t// step is scaled to two-thirds distance, preserving configured travel speed.\n\tprivate static final long MOVEMENT_STEP_INTERVAL_TICKS = 2L;",
    "combat two-tick movement interval",
)
replace_once(
    combat,
    "\t\t\t\t// takeStep() uses the pet's saved /aspet speed value. Matching the\n\t\t\t\t// normal follow task's three-tick interval keeps the actual travel\n\t\t\t\t// speed identical while combat still starts immediately.",
    "\t\t\t\t// animateWalk() and takeStep() remain paired in the same update.\n\t\t\t\t// The two-thirds step scale preserves the original travel speed.",
    "combat synchronized movement comment",
)

entities = root / "entity/ModEntities.java"
replace_once(
    entities,
    ".updateInterval(3)",
    ".updateInterval(1)",
    "one-tick entity tracking interval",
)

# Strict safeguards: this must remain the original movement implementation,
# merely running more often with a proportionally shorter step.
pet_source = pet.read_text(encoding="utf-8")
if pet_source.count("LIGHT_SMOOTH_STEP_SCALE = 2.0D / 3.0D") != 1:
    raise SystemExit("Light smoothing scale was not installed exactly once")
if "takeSmoothStep" in pet_source or "smoothStepPhase" in pet_source:
    raise SystemExit("Rejected prior stateful smooth-movement implementation")
if "public abstract void takeStep();" not in pet_source:
    raise SystemExit("Original takeStep API was changed")

for type_name in ("NeedyChildPet", "DemonPet", "SillyWalkerPet"):
    source = (root / f"types/{type_name}.java").read_text(encoding="utf-8")
    if source.count("this.speed * LIGHT_SMOOTH_STEP_SCALE") != 1:
        raise SystemExit(f"{type_name} does not have exactly one scaled original step")
    if "public void takeStep()" not in source:
        raise SystemExit(f"{type_name} original takeStep signature changed")

for path in (walk_loc, walk_player, chase, combat):
    source = path.read_text(encoding="utf-8")
    if "takeSmoothStep" in source:
        raise SystemExit(f"Stateful smooth movement remained in {path}")

if walk_loc.read_text(encoding="utf-8").count("runTaskLater(2)") != 1:
    raise SystemExit("WalkLocTask is not exactly two-tick cadence")
if walk_player.read_text(encoding="utf-8").count("runTaskLater(2)") != 1:
    raise SystemExit("WalkPlayerTask is not exactly two-tick cadence")
if chase.read_text(encoding="utf-8").count("runTaskLater(2)") != 2:
    raise SystemExit("ChasePathTask two-tick cadence was not applied exactly twice")
if "if (this.iters > 30)" not in chase.read_text(encoding="utf-8"):
    raise SystemExit("Chase timeout was not scaled to preserve real time")
if "MOVEMENT_STEP_INTERVAL_TICKS = 2L" not in combat.read_text(encoding="utf-8"):
    raise SystemExit("Combat movement is not using two-tick cadence")
if entities.read_text(encoding="utf-8").count(".updateInterval(1)") != 1:
    raise SystemExit("Entity tracking interval is not one tick")

# The animation and movement must remain adjacent and ordered exactly as before.
for path in (walk_loc, walk_player, chase):
    source = path.read_text(encoding="utf-8")
    if "this.pet.animateWalk();\n\t\tthis.pet.takeStep();" not in source:
        raise SystemExit(f"Movement/animation pairing changed in {path}")
combat_source = combat.read_text(encoding="utf-8")
if "pet.animateWalk();\n\t\t\t\t\tpet.takeStep();" not in combat_source:
    raise SystemExit("Combat movement/animation pairing changed")

print("Applied lightweight two-tick synchronized movement with original direction logic")
