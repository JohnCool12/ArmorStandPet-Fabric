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


# The original movement model travels one configured speed-sized step every
# three ticks. Split the exact same distance into three equal one-tick substeps.
# Target selection, path nodes, animation cadence, attack cooldowns, collision
# checks, stopping ranges and teleport thresholds remain otherwise unchanged.
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

# Strict source-level safeguards.
pet_source = pet.read_text(encoding="utf-8")
for marker in [
    "SMOOTH_STEP_SCALE = 1.0D / 3.0D",
    "public final void takeSmoothStep()",
    "this.takeStep(SMOOTH_STEP_SCALE)",
    "this.smoothStepPhase = (this.smoothStepPhase + 1) % 3",
]:
    if marker not in pet_source:
        raise SystemExit(f"Smooth movement core missing {marker!r}")

for path in (walk_loc, walk_player, chase, combat):
    source = path.read_text(encoding="utf-8")
    if "takeSmoothStep()" not in source:
        raise SystemExit(f"Smooth movement call missing from {path}")

if "MOVEMENT_STEP_INTERVAL_TICKS = 1L" not in combat.read_text(encoding="utf-8"):
    raise SystemExit("Combat pursuit is not using one-tick movement")
if "if (this.iters > 60)" not in chase.read_text(encoding="utf-8"):
    raise SystemExit("Chase timeout was not scaled to preserve real-time behavior")
if walk_loc.read_text(encoding="utf-8").count("runTaskLater(1)") != 1:
    raise SystemExit("WalkLocTask cadence is not exactly one tick")
if walk_player.read_text(encoding="utf-8").count("runTaskLater(1)") != 1:
    raise SystemExit("WalkPlayerTask cadence is not exactly one tick")
if chase.read_text(encoding="utf-8").count("runTaskLater(1)") != 2:
    raise SystemExit("ChasePathTask one-tick cadence was not applied exactly twice")

print("Applied smooth one-tick movement while preserving original three-tick travel distance")
