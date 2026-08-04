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
# Walking poses are interpolated between the original keyframes on those same
# three ticks, so movement and animation advance from one shared clock.
pet = root / "types/Pet.java"
replace_once(
    pet,
    "\t// Which stage of the walking animation is this armorstand in?\n\tprotected int walkStage;",
    "\t// Which stage of the walking animation is this armorstand in?\n\tprotected int walkStage;\n\n\tprivate static final double SMOOTH_STEP_SCALE = 1.0D / 3.0D;\n\tprivate int smoothStepPhase;\n\tprivate EulerAngle[] smoothStartPose;\n\tprivate EulerAngle[] smoothTargetPose;",
    "smooth movement state",
)
replace_once(
    pet,
    "\tpublic abstract void takeStep();",
    "\t/** Preserves the original full movement step for compatibility. */\n\tpublic final void takeStep()\n\t{\n\t\tthis.takeStep(1.0D);\n\t}\n\n\t/** Moves one scaled portion of the pet's configured speed. */\n\tpublic abstract void takeStep(double distanceScale);\n\n\t/**\n\t * Executes one of three equal per-tick substeps and interpolates the armor\n\t * stand pose toward the next original walking keyframe on the same clock.\n\t */\n\tpublic final void takeSmoothStep()\n\t{\n\t\tif (this.smoothStepPhase == 0 || this.smoothStartPose == null || this.smoothTargetPose == null)\n\t\t{\n\t\t\tthis.smoothStartPose = this.captureWalkPose();\n\t\t\tthis.animateWalk();\n\t\t\tthis.smoothTargetPose = this.captureWalkPose();\n\t\t}\n\n\t\tdouble progress = (this.smoothStepPhase + 1) / 3.0D;\n\t\tthis.applyInterpolatedWalkPose(progress);\n\t\tthis.takeStep(SMOOTH_STEP_SCALE);\n\t\tthis.smoothStepPhase = (this.smoothStepPhase + 1) % 3;\n\t}\n\n\t/** Start the next movement cycle from the pet's current visible pose. */\n\tpublic final void resetSmoothMovementCycle()\n\t{\n\t\tthis.smoothStepPhase = 0;\n\t\tthis.smoothStartPose = null;\n\t\tthis.smoothTargetPose = null;\n\t}\n\n\tprivate EulerAngle[] captureWalkPose()\n\t{\n\t\treturn new EulerAngle[] {\n\t\t\t\tthis.stand.getHeadPoseAngle(),\n\t\t\t\tthis.stand.getBodyPoseAngle(),\n\t\t\t\tthis.stand.getLeftArmPoseAngle(),\n\t\t\t\tthis.stand.getRightArmPoseAngle(),\n\t\t\t\tthis.stand.getLeftLegPoseAngle(),\n\t\t\t\tthis.stand.getRightLegPoseAngle()\n\t\t};\n\t}\n\n\tprivate void applyInterpolatedWalkPose(double progress)\n\t{\n\t\tthis.stand.setHeadPose(interpolate(this.smoothStartPose[0], this.smoothTargetPose[0], progress));\n\t\tthis.stand.setBodyPose(interpolate(this.smoothStartPose[1], this.smoothTargetPose[1], progress));\n\t\tthis.stand.setLeftArmPose(interpolate(this.smoothStartPose[2], this.smoothTargetPose[2], progress));\n\t\tthis.stand.setRightArmPose(interpolate(this.smoothStartPose[3], this.smoothTargetPose[3], progress));\n\t\tthis.stand.setLeftLegPose(interpolate(this.smoothStartPose[4], this.smoothTargetPose[4], progress));\n\t\tthis.stand.setRightLegPose(interpolate(this.smoothStartPose[5], this.smoothTargetPose[5], progress));\n\t}\n\n\tprivate static EulerAngle interpolate(EulerAngle start, EulerAngle target, double progress)\n\t{\n\t\treturn new EulerAngle(\n\t\t\t\tstart.x + (target.x - start.x) * progress,\n\t\t\t\tstart.y + (target.y - start.y) * progress,\n\t\t\t\tstart.z + (target.z - start.z) * progress);\n\t}",
    "scaled movement and interpolated animation API",
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
    ".runTaskLater(3);",
    ".runTaskLater(1);",
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
    "\t\t\tstand.setRightArmPose(RIGHT_ARM_ATTACK_POSE);",
    "\t\t\tpet.resetSmoothMovementCycle();\n\t\t\tstand.setRightArmPose(RIGHT_ARM_ATTACK_POSE);",
    "combat attack-pose movement reset",
)
replace_once(
    combat,
    "\t\t\t\t\tpet.animateWalk();\n\t\t\t\t\tpet.takeStep();",
    "\t\t\t\t\tpet.takeSmoothStep();\n\t\t\t\t\t// Interpolated walking updates both arms. Keep the raised attack arm\n\t\t\t\t\t// authoritative if the target moves during the nine-tick swing pose.\n\t\t\t\t\tif (state.animationResetTick > now)\n\t\t\t\t\t\tstand.setRightArmPose(RIGHT_ARM_ATTACK_POSE);",
    "combat smooth synchronized substep",
)
replace_once(
    combat,
    "\t\t\t\t// takeStep() uses the pet's saved /aspet speed value. Matching the\n\t\t\t\t// normal follow task's three-tick interval keeps the actual travel\n\t\t\t\t// speed identical while combat still starts immediately.",
    "\t\t\t\t// takeSmoothStep() uses one third of the configured /aspet speed\n\t\t\t\t// every tick, preserving the original total travel speed.",
    "combat movement comment",
)
replace_once(
    combat,
    "\t\t\t\tpet.walkFlat();\n\t\t\t\tstate.animationResetTick = 0L;",
    "\t\t\t\tpet.walkFlat();\n\t\t\t\tpet.resetSmoothMovementCycle();\n\t\t\t\tstate.animationResetTick = 0L;",
    "combat post-attack movement reset",
)

# Send custom-entity movement tracking every tick as well. The old three-tick
# tracker cadence could otherwise hide two of the three new server substeps.
entities = root / "entity/ModEntities.java"
replace_once(
    entities,
    ".updateInterval(3)",
    ".updateInterval(1)",
    "one-tick entity tracking interval",
)

# Strict source-level safeguards.
pet_source = pet.read_text(encoding="utf-8")
for marker in [
    "SMOOTH_STEP_SCALE = 1.0D / 3.0D",
    "public final void takeSmoothStep()",
    "public final void resetSmoothMovementCycle()",
    "this.stand.getHeadPoseAngle()",
    "this.applyInterpolatedWalkPose(progress)",
    "private static EulerAngle interpolate",
    "this.takeStep(SMOOTH_STEP_SCALE)",
    "this.smoothStepPhase = (this.smoothStepPhase + 1) % 3",
]:
    if marker not in pet_source:
        raise SystemExit(f"Smooth movement core missing {marker!r}")

for path in (walk_loc, walk_player, chase, combat):
    source = path.read_text(encoding="utf-8")
    if "takeSmoothStep()" not in source:
        raise SystemExit(f"Smooth movement call missing from {path}")

combat_source = combat.read_text(encoding="utf-8")
if "MOVEMENT_STEP_INTERVAL_TICKS = 1L" not in combat_source:
    raise SystemExit("Combat pursuit is not using one-tick movement")
if combat_source.count("resetSmoothMovementCycle()") != 2:
    raise SystemExit("Combat pose transitions are not synchronized with smooth movement")
if "state.animationResetTick > now" not in combat_source:
    raise SystemExit("Moving swing does not preserve its raised attack arm")
if combat_source.count("stand.setRightArmPose(RIGHT_ARM_ATTACK_POSE)") < 2:
    raise SystemExit("Attack arm is not applied on both hit and moving swing paths")
if "if (this.iters > 60)" not in chase.read_text(encoding="utf-8"):
    raise SystemExit("Chase timeout was not scaled to preserve real-time behavior")
if walk_loc.read_text(encoding="utf-8").count("runTaskLater(1)") != 1:
    raise SystemExit("WalkLocTask cadence is not exactly one tick")
if walk_player.read_text(encoding="utf-8").count("runTaskLater(1)") != 1:
    raise SystemExit("WalkPlayerTask cadence is not exactly one tick")
if chase.read_text(encoding="utf-8").count("runTaskLater(1)") != 2:
    raise SystemExit("ChasePathTask one-tick cadence was not applied exactly twice")
if ".updateInterval(1)" not in entities.read_text(encoding="utf-8"):
    raise SystemExit("Custom entity tracking is not updating every tick")

print("Applied one-tick movement, pose interpolation, combat synchronization, and entity tracking")
