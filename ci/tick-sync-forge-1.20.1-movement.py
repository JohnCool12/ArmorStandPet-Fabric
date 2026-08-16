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


# Keep the original configured travel speed, but update movement and animation
# every tick instead of once every three ticks. All normal walking and combat
# pursuit use the same shared routine below.
pet = root / "types/Pet.java"
replace_once(
    pet,
    "\tpublic abstract void takeStep();",
    "\tpublic abstract void takeStep();\n\n"
    "\t/** Returns one tick of the original three-tick movement distance. */\n"
    "\tprotected final double getPerTickSpeed()\n"
    "\t{\n"
    "\t\treturn this.speed / 3.0D;\n"
    "\t}\n\n"
    "\t/**\n"
    "\t * Shared movement path for normal walking, path following and combat.\n"
    "\t * Facing, animation and position are updated together every server tick.\n"
    "\t */\n"
    "\tpublic final void walkOneTickToward(Pos destination)\n"
    "\t{\n"
    "\t\tthis.faceLoc(destination);\n"
    "\t\tthis.animateWalk();\n"
    "\t\tthis.takeStep();\n"
    "\t}\n\n"
    "\t/** Same per-tick movement path while preserving player head tracking. */\n"
    "\tpublic final void walkOneTickToward(ServerPlayer player)\n"
    "\t{\n"
    "\t\tthis.facePlayer(player);\n"
    "\t\tthis.animateWalk();\n"
    "\t\tthis.takeStep();\n"
    "\t}",
    "shared per-tick movement routine",
)

for type_name in ("NeedyChildPet", "DemonPet", "SillyWalkerPet"):
    type_path = root / f"types/{type_name}.java"
    replace_once(
        type_path,
        "Vec walk = standDirection.normalize().multiply(this.speed);",
        "Vec walk = standDirection.normalize().multiply(this.getPerTickSpeed());",
        f"{type_name} per-tick movement distance",
    )

walk_player = root / "tasks/WalkPlayerTask.java"
replace_once(
    walk_player,
    "\t\tthis.pet.facePlayer(this.dest);\n\t\tthis.pet.animateWalk();\n\t\tthis.pet.takeStep();",
    "\t\tthis.pet.walkOneTickToward(this.dest);",
    "WalkPlayerTask shared movement",
)
replace_once(
    walk_player,
    ")).runTaskLater(3);",
    ")).runTaskLater(1);",
    "WalkPlayerTask one-tick cadence",
)

walk_loc = root / "tasks/WalkLocTask.java"
replace_once(
    walk_loc,
    "\t\tthis.pet.faceLoc(this.dest);\n\t\tthis.pet.animateWalk();\n\t\tthis.pet.takeStep();",
    "\t\tthis.pet.walkOneTickToward(this.dest);",
    "WalkLocTask shared movement",
)
replace_once(
    walk_loc,
    ")).runTaskLater(3);",
    ")).runTaskLater(1);",
    "WalkLocTask one-tick cadence",
)

chase = root / "tasks/ChasePathTask.java"
replace_once(
    chase,
    "\t\tif (this.iters > 20)",
    "\t\tif (this.iters > 60)",
    "real-time-equivalent chase timeout",
)
replace_once(
    chase,
    "\t\tthis.pet.faceLoc(currLoc);\n\t\tthis.pet.animateWalk();\n\t\tthis.pet.takeStep();",
    "\t\tthis.pet.walkOneTickToward(currLoc);",
    "ChasePathTask shared movement",
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
    "\t// Normal WalkPlayerTask takes one speed-sized step every three ticks. Using\n"
    "\t// the same cadence here makes combat pursuit obey /aspet speed identically.\n"
    "\tprivate static final long MOVEMENT_STEP_INTERVAL_TICKS = 3L;",
    "\t// Normal walking and combat both update movement and animation every tick.\n"
    "\tprivate static final long MOVEMENT_STEP_INTERVAL_TICKS = 1L;",
    "combat one-tick cadence",
)
replace_once(
    combat,
    "\t\t\tPos targetPosition = new Pos(level, target.getX(), target.getY(), target.getZ(),\n"
    "\t\t\t\t\ttarget.getYRot(), target.getXRot());\n"
    "\t\t\tpet.faceLoc(targetPosition);\n\n"
    "\t\t\tif (distanceSquared > ATTACK_RANGE_SQUARED)\n"
    "\t\t\t{\n"
    "\t\t\t\t// takeStep() uses the pet's saved /aspet speed value. Matching the\n"
    "\t\t\t\t// normal follow task's three-tick interval keeps the actual travel\n"
    "\t\t\t\t// speed identical while combat still starts immediately.\n"
    "\t\t\t\tif (pet.isMobile && now >= state.nextMovementTick)\n"
    "\t\t\t\t{\n"
    "\t\t\t\t\tpet.animateWalk();\n"
    "\t\t\t\t\tpet.takeStep();\n"
    "\t\t\t\t\tstate.nextMovementTick = now + MOVEMENT_STEP_INTERVAL_TICKS;\n"
    "\t\t\t\t}\n"
    "\t\t\t\tcontinue;\n"
    "\t\t\t}",
    "\t\t\tPos targetPosition = new Pos(level, target.getX(), target.getY(), target.getZ(),\n"
    "\t\t\t\t\ttarget.getYRot(), target.getXRot());\n\n"
    "\t\t\tif (distanceSquared > ATTACK_RANGE_SQUARED)\n"
    "\t\t\t{\n"
    "\t\t\t\tif (pet.isMobile && now >= state.nextMovementTick)\n"
    "\t\t\t\t{\n"
    "\t\t\t\t\t// Use exactly the same facing, animation and movement routine as\n"
    "\t\t\t\t\t// normal walking so combat pursuit cannot drift into a separate path.\n"
    "\t\t\t\t\tpet.walkOneTickToward(targetPosition);\n"
    "\t\t\t\t\tstate.nextMovementTick = now + MOVEMENT_STEP_INTERVAL_TICKS;\n"
    "\t\t\t\t}\n"
    "\t\t\t\tcontinue;\n"
    "\t\t\t}\n\n"
    "\t\t\tpet.faceLoc(targetPosition);",
    "combat shared movement path",
)

# Strict safeguards: no previous substep state, unchanged combat timings, and
# every movement loop routed through the same per-tick helper.
pet_source = pet.read_text(encoding="utf-8")
for marker in [
    "protected final double getPerTickSpeed()",
    "return this.speed / 3.0D;",
    "public final void walkOneTickToward(Pos destination)",
    "public final void walkOneTickToward(ServerPlayer player)",
]:
    if marker not in pet_source:
        raise SystemExit(f"Per-tick movement core missing {marker!r}")
for forbidden in ["smoothStepPhase", "takeSmoothStep", "SMOOTH_STEP_SCALE"]:
    if forbidden in pet_source:
        raise SystemExit(f"Rejected previous substep implementation marker {forbidden!r}")

for path, expected_calls in [
    (walk_player, 1),
    (walk_loc, 1),
    (chase, 1),
    (combat, 1),
]:
    source = path.read_text(encoding="utf-8")
    if source.count("walkOneTickToward(") != expected_calls:
        raise SystemExit(f"Shared movement call count mismatch in {path}")

if walk_player.read_text(encoding="utf-8").count("runTaskLater(1)") != 1:
    raise SystemExit("WalkPlayerTask is not updating every tick")
if walk_loc.read_text(encoding="utf-8").count("runTaskLater(1)") != 1:
    raise SystemExit("WalkLocTask is not updating every tick")
if chase.read_text(encoding="utf-8").count("runTaskLater(1)") != 2:
    raise SystemExit("ChasePathTask is not updating every tick")
if "if (this.iters > 60)" not in chase.read_text(encoding="utf-8"):
    raise SystemExit("Chase timeout no longer preserves its original real-time duration")

combat_source = combat.read_text(encoding="utf-8")
for marker in [
    "ATTACK_COOLDOWN_TICKS = 20L",
    "ATTACK_ANIMATION_TICKS = 9L",
    "MOVEMENT_STEP_INTERVAL_TICKS = 1L",
    "pet.walkOneTickToward(targetPosition)",
]:
    if marker not in combat_source:
        raise SystemExit(f"Combat behavior missing {marker!r}")
if "pet.animateWalk();\n\t\t\t\t\tpet.takeStep();" in combat_source:
    raise SystemExit("Separate combat movement implementation remained")

print("Applied lightweight tick-synchronized walking and unified combat pursuit")
