from pathlib import Path

root = Path("project/src/main/java/io/github/kyzderp/armorstandpet")


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Expected one {label} in {path}, found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


# Preserve every pet type's original takeStep implementation while allowing
# combat pursuit to divide one configured movement step into smaller updates.
pet = root / "types/Pet.java"
replace_once(
    pet,
    "\tpublic abstract void takeStep();\n",
    """\t/**
\t * Takes a fractional movement step without permanently changing /aspet speed.
\t * The concrete pet still performs its original terrain and movement logic.
\t */
\tpublic void takeScaledStep(double scale)
\t{
\t\tif (!Double.isFinite(scale) || scale <= 0.0D)
\t\t\treturn;

\t\tdouble configuredSpeed = this.speed;
\t\tthis.speed = configuredSpeed * scale;
\t\ttry
\t\t{
\t\t\tthis.takeStep();
\t\t}
\t\tfinally
\t\t{
\t\t\tthis.speed = configuredSpeed;
\t\t}
\t}

\tpublic abstract void takeStep();
""",
    "scaled movement helper",
)

combat = root / "combat/OwnerAttackCombatController.java"
replace_once(
    combat,
    """\t// Normal WalkPlayerTask takes one speed-sized step every three ticks. Using
\t// the same cadence here makes combat pursuit obey /aspet speed identically.
\tprivate static final long MOVEMENT_STEP_INTERVAL_TICKS = 3L;
""",
    """\t// Send a smaller pursuit update every tick. Three one-third steps preserve
\t// the old travel distance and /aspet speed while removing large chase jumps.
\tprivate static final long MOVEMENT_UPDATE_INTERVAL_TICKS = 1L;
\tprivate static final double MOVEMENT_STEP_SCALE = 1.0D / 3.0D;
\t// Advance the existing walk cycle more often, but not so fast that its
\t// eight-stage animation becomes frantic.
\tprivate static final long WALK_ANIMATION_INTERVAL_TICKS = 2L;
""",
    "combat movement constants",
)
replace_once(
    combat,
    """\t\t\tif (distanceSquared > ATTACK_RANGE_SQUARED)
\t\t\t{
\t\t\t\t// takeStep() uses the pet's saved /aspet speed value. Matching the
\t\t\t\t// normal follow task's three-tick interval keeps the actual travel
\t\t\t\t// speed identical while combat still starts immediately.
\t\t\t\tif (pet.isMobile && now >= state.nextMovementTick)
\t\t\t\t{
\t\t\t\t\tpet.animateWalk();
\t\t\t\t\tpet.takeStep();
\t\t\t\t\tstate.nextMovementTick = now + MOVEMENT_STEP_INTERVAL_TICKS;
\t\t\t\t}
\t\t\t\tcontinue;
\t\t\t}
""",
    """\t\t\tif (distanceSquared > ATTACK_RANGE_SQUARED)
\t\t\t{
\t\t\t\tif (pet.isMobile && now >= state.nextMovementTick)
\t\t\t\t{
\t\t\t\t\t// Position and animation are driven by the same combat state instead
\t\t\t\t\t// of a coarse three-tick movement jump.
\t\t\t\t\tif (now >= state.nextWalkAnimationTick)
\t\t\t\t\t{
\t\t\t\t\t\tpet.animateWalk();
\t\t\t\t\t\tstate.nextWalkAnimationTick = now + WALK_ANIMATION_INTERVAL_TICKS;
\t\t\t\t\t}

\t\t\t\t\t// animateWalk updates both arms. Preserve the visible attack arm if
\t\t\t\t\t// the mob moves away during the nine-tick swing animation.
\t\t\t\t\tif (state.animationResetTick > now)
\t\t\t\t\t\tstand.setRightArmPose(RIGHT_ARM_ATTACK_POSE);

\t\t\t\t\tpet.takeScaledStep(MOVEMENT_STEP_SCALE);
\t\t\t\t\tstate.nextMovementTick = now + MOVEMENT_UPDATE_INTERVAL_TICKS;
\t\t\t\t}
\t\t\t\tcontinue;
\t\t\t}
""",
    "smooth combat pursuit",
)
replace_once(
    combat,
    """\t\tprivate long nextAttackTick;
\t\tprivate long nextMovementTick;
\t\tprivate long animationResetTick;
""",
    """\t\tprivate long nextAttackTick;
\t\tprivate long nextMovementTick;
\t\tprivate long nextWalkAnimationTick;
\t\tprivate long animationResetTick;
""",
    "walk animation tick state",
)
replace_once(
    combat,
    """\t\t\tthis.nextAttackTick = nextAttackTick;
\t\t\tthis.nextMovementTick = nextMovementTick;
""",
    """\t\t\tthis.nextAttackTick = nextAttackTick;
\t\t\tthis.nextMovementTick = nextMovementTick;
\t\t\tthis.nextWalkAnimationTick = nextMovementTick;
""",
    "walk animation tick initialization",
)

pet_source = pet.read_text(encoding="utf-8")
combat_source = combat.read_text(encoding="utf-8")
for marker in (
    "public void takeScaledStep(double scale)",
    "this.speed = configuredSpeed * scale",
    "this.speed = configuredSpeed",
):
    if marker not in pet_source:
        raise SystemExit(f"Scaled movement helper missing {marker!r}")
for marker in (
    "MOVEMENT_UPDATE_INTERVAL_TICKS = 1L",
    "MOVEMENT_STEP_SCALE = 1.0D / 3.0D",
    "WALK_ANIMATION_INTERVAL_TICKS = 2L",
    "pet.takeScaledStep(MOVEMENT_STEP_SCALE)",
    "state.nextWalkAnimationTick",
    "stand.setRightArmPose(RIGHT_ARM_ATTACK_POSE)",
):
    if marker not in combat_source:
        raise SystemExit(f"Smooth combat pursuit missing {marker!r}")
if "MOVEMENT_STEP_INTERVAL_TICKS = 3L" in combat_source:
    raise SystemExit("Old three-tick full-step combat pursuit remained")

print("Installed synchronized high-frequency combat movement and animation")
