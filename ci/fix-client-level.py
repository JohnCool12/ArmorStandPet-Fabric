from pathlib import Path
import re

path = Path("project/src/main/java/io/github/kyzderp/armorstandpet/entity/PetArmorStandEntity.java")
source = path.read_text(encoding="utf-8")

# The 26.2 port used a covariant ServerLevel return here. That is invalid for
# an entity type that is also instantiated in ClientLevel from spawn packets:
# the generated bridge method calls the override and casts ClientLevel to
# ServerLevel during Entity's constructor (Fabric permission context).
pattern = re.compile(
    r"(@Override\s+public\s+)ServerLevel(\s+level\s*\(\s*\)\s*\{\s*)"
    r"return\s+\(ServerLevel\)\s*super\.level\s*\(\s*\)\s*;"
    r"(\s*\})",
    re.DOTALL,
)
replacement = r"\1Level\2return super.level();\3"
updated, count = pattern.subn(replacement, source)
if count != 1:
    raise SystemExit(f"Expected exactly one unsafe ServerLevel level() override, found {count}")

path.write_text(updated, encoding="utf-8")
print("Replaced unsafe ServerLevel level() override with side-safe Level override")
