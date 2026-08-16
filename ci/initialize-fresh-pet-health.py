from pathlib import Path
import re

root = Path("project/src/main/java/io/github/kyzderp/armorstandpet")
pet_path = root / "types/Pet.java"
storage_path = root / "storage/PetStorage.java"

# Every newly constructed Pet begins with a full internal ArmorStand health
# value. The explicit per-Pet health field is added by the following 1.21.1 API
# adaptation step and will also begin at 20.
pet = pet_path.read_text(encoding="utf-8")
old_constructor_block = """\t\tif (this.stand != null)
\t\t{
\t\t\tthis.stand.setGravity(false);
"""
new_constructor_block = """\t\tif (this.stand != null)
\t\t{
\t\t\tthis.stand.setHealth(20.0F);
\t\t\tthis.stand.setGravity(false);
"""
if pet.count(old_constructor_block) != 1:
    raise SystemExit(
        f"Expected one Pet constructor stand-initialization block, found {pet.count(old_constructor_block)}"
    )
pet = pet.replace(old_constructor_block, new_constructor_block, 1)
pet_path.write_text(pet, encoding="utf-8")

# loadPet() restores the same saved pet after a restart and therefore preserves
# its remaining health. loadPetSettings() is used when an armor stand becomes a
# newly created/replacement pet. It may reuse preferences, but health and death
# state belong to the old pet and must never transfer to the new entity.
storage = storage_path.read_text(encoding="utf-8")
method_match = re.search(
    r"public static Pet loadPetSettings\(String owner, String world, PetType type, PetArmorStandEntity stand\)"
    r"(?P<body>.*?)\n\t}\n\n\tprivate static ServerLevel getWorld",
    storage,
    flags=re.DOTALL,
)
if method_match is None:
    raise SystemExit("Could not locate PetStorage.loadPetSettings")

body = method_match.group("body")
load_pattern = re.compile(
    r"(?P<indent>^[ \t]*)Pet pet = Pet\.createPet\(type, owner, stand\);\s*\n"
    r"(?P=indent)pet\.deserializeSettings\(data\);",
    flags=re.MULTILINE,
)
load_matches = list(load_pattern.finditer(body))
if len(load_matches) != 1:
    raise SystemExit(
        f"Expected one loadPetSettings deserialize sequence, found {len(load_matches)}"
    )

indent = load_matches[0].group("indent")
replacement = (
    f"{indent}// This is a new pet instance. Do not inherit mortality state from an\n"
    f"{indent}// earlier pet belonging to the same owner and type.\n"
    f"{indent}data.mortalDead = false;\n"
    f"{indent}data.health = 20.0F;\n\n"
    f"{indent}Pet pet = Pet.createPet(type, owner, stand);\n"
    f"{indent}pet.deserializeSettings(data);"
)
new_body = load_pattern.sub(replacement, body, count=1)
storage = storage[:method_match.start("body")] + new_body + storage[method_match.end("body"):]
storage_path.write_text(storage, encoding="utf-8")

# The reset must exist only in loadPetSettings. The normal loadPet path must
# continue restoring the same pet's persisted health after a server restart.
pet_check = pet_path.read_text(encoding="utf-8")
storage_check = storage_path.read_text(encoding="utf-8")
if pet_check.count("this.stand.setHealth(20.0F);") != 1:
    raise SystemExit("Fresh Pet constructor must initialize entity health exactly once")
if storage_check.count("data.health = 20.0F;") != 1:
    raise SystemExit("Only the new-pet settings path may force saved health to 20")
if storage_check.count("data.mortalDead = false;") != 1:
    raise SystemExit("Only the new-pet settings path may clear saved death state")

print("Separated newly created pet health from restored pet health")
