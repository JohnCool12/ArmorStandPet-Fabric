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

replacements = {
    "entity/StandFactory.java": [("original.level()", "original.serverLevel()", 1)],
    "types/Pet.java": [("this.stand.level()", "this.stand.serverLevel()", 7)],
    "types/DemonPet.java": [("this.stand.level()", "this.stand.serverLevel()", 2)],
    "storage/PetStorage.java": [("stand.level()", "stand.serverLevel()", 1)],
    "tasks/WalkPlayerTask.java": [("this.pet.getStand().level()", "this.pet.getStand().serverLevel()", 2)],
    "admincommands/TpCommand.java": [("pet.getStand().level()", "pet.getStand().serverLevel()", 1)],
    "actions/DoneDitchingAction.java": [("stand.level()", "stand.serverLevel()", 1)],
}

changed_calls = 0
for relative, file_replacements in replacements.items():
    path = root / relative
    text = path.read_text(encoding="utf-8")
    for old, new, expected in file_replacements:
        found = text.count(old)
        if found != expected:
            raise SystemExit(f"Expected {expected} occurrences of {old!r} in {relative}, found {found}")
        text = text.replace(old, new)
        changed_calls += found
    path.write_text(text, encoding="utf-8")

if changed_calls != 15:
    raise SystemExit(f"Expected to redirect 15 server-only level calls, redirected {changed_calls}")

print("Made entity level() client-safe and redirected 15 server-only callers to serverLevel()")
