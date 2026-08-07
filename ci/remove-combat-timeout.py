from pathlib import Path
import re

path = Path("project/src/main/java/io/github/kyzderp/armorstandpet/combat/OwnerAttackCombatController.java")
source = path.read_text(encoding="utf-8")

# Combat used to expire after 300 ticks (15 seconds), even when the target was
# still alive. Remove the independent timer so the target's real alive/removal
# state controls when combat ends.
source, constant_count = re.subn(
    r"\n\tprivate static final long PURSUIT_TIMEOUT_TICKS = 300L;",
    "",
    source,
    count=1,
)
if constant_count != 1:
    raise SystemExit(f"Expected one pursuit timeout constant, found {constant_count}")

old_creation = "new AttackState(pet, target, now + PURSUIT_TIMEOUT_TICKS, now, now)"
new_creation = "new AttackState(pet, target, now, now)"
if source.count(old_creation) != 1:
    raise SystemExit("Could not find timed AttackState construction")
source = source.replace(old_creation, new_creation, 1)

source, timeout_block_count = re.subn(
    r"\n\t\t\tif \(now > state\.expiresAtTick\)\n"
    r"\t\t\t\{\n"
    r"\t\t\t\tfinish\(iterator, state\);\n"
    r"\t\t\t\tcontinue;\n"
    r"\t\t\t\}\n",
    "\n",
    source,
    count=1,
)
if timeout_block_count != 1:
    raise SystemExit(f"Expected one timeout stop block, found {timeout_block_count}")

source, field_count = re.subn(
    r"\n\t\tprivate final long expiresAtTick;",
    "",
    source,
    count=1,
)
if field_count != 1:
    raise SystemExit(f"Expected one expiresAtTick field, found {field_count}")

old_ctor = "private AttackState(Pet pet, Mob target, long expiresAtTick,\n\t\t\t\tlong nextAttackTick, long nextMovementTick)"
new_ctor = "private AttackState(Pet pet, Mob target, long nextAttackTick, long nextMovementTick)"
if source.count(old_ctor) != 1:
    raise SystemExit("Could not find timed AttackState constructor")
source = source.replace(old_ctor, new_ctor, 1)

assignment = "\n\t\t\tthis.expiresAtTick = expiresAtTick;"
if source.count(assignment) != 1:
    raise SystemExit("Could not find expiresAtTick assignment")
source = source.replace(assignment, "", 1)

for forbidden in ["PURSUIT_TIMEOUT_TICKS", "expiresAtTick"]:
    if forbidden in source:
        raise SystemExit(f"Combat timeout remained after fix: {forbidden}")

required = [
    "target == null || target.isRemoved() || !target.isAlive()",
    "if (target.level() != level)",
    "distanceSquared > MAX_PURSUIT_RANGE_SQUARED",
    "new AttackState(pet, target, now, now)",
]
for text in required:
    if text not in source:
        raise SystemExit(f"Required target-lifetime check missing: {text}")

path.write_text(source, encoding="utf-8")
print("Removed the false 15-second combat timeout; combat now follows actual target life")
