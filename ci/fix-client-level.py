from pathlib import Path
import re

root = Path("project/src/main/java/io/github/kyzderp/armorstandpet")
entity_path = root / "entity/PetArmorStandEntity.java"
source = entity_path.read_text(encoding="utf-8")

pattern = re.compile(
    r"(@Override\s+public\s+)ServerLevel(\s+level\s*\(\s*\)\s*\{\s*)"
    r"return\s+\(ServerLevel\)\s*super\.level\s*\(\s*\)\s*;"
    r"(\s*\})",
    re.DOTALL,
)
replacement = (
    r"\1Level\2return super.level();\3\n\n"
    "\tpublic ServerLevel serverLevel()\n"
    "\t{\n"
    "\t\tLevel level = super.level();\n"
    "\t\tif (level instanceof ServerLevel serverLevel)\n"
    "\t\t\treturn serverLevel;\n"
    "\t\tthrow new IllegalStateException(\"Server-only ArmorStandPet operation attempted in a client level\");\n"
    "\t}"
)
updated, count = pattern.subn(replacement, source)
if count != 1:
    raise SystemExit(f"Expected exactly one unsafe ServerLevel level() override, found {count}")
entity_path.write_text(updated, encoding="utf-8")

# Each of these classes performs server-only pet work. Replace every access on
# a PetArmorStandEntity in these audited classes rather than depending on a
# brittle line/count list.
replacements = {
    "entity/StandFactory.java": ("original.level()", "original.serverLevel()"),
    "types/Pet.java": ("this.stand.level()", "this.stand.serverLevel()"),
    "types/DemonPet.java": ("this.stand.level()", "this.stand.serverLevel()"),
    "storage/PetStorage.java": ("stand.level()", "stand.serverLevel()"),
    "tasks/WalkPlayerTask.java": ("this.pet.getStand().level()", "this.pet.getStand().serverLevel()"),
    "admincommands/TpCommand.java": ("pet.getStand().level()", "pet.getStand().serverLevel()"),
    "actions/DoneDitchingAction.java": ("stand.level()", "stand.serverLevel()"),
}

changed_calls = 0
for relative, (old, new) in replacements.items():
    path = root / relative
    text = path.read_text(encoding="utf-8")
    found = text.count(old)
    if found < 1:
        raise SystemExit(f"Expected at least one occurrence of {old!r} in {relative}")
    text = text.replace(old, new)
    changed_calls += found
    path.write_text(text, encoding="utf-8")

if changed_calls < 15:
    raise SystemExit(f"Expected to redirect at least 15 server-only level calls, redirected {changed_calls}")

print(f"Made entity level() client-safe and redirected {changed_calls} server-only callers to serverLevel()")
