from pathlib import Path
import re

root = Path("project/src/main/java/io/github/kyzderp/armorstandpet")
pet_path = root / "types/Pet.java"
storage_path = root / "storage/PetStorage.java"

# Every newly constructed Pet owns its own health field. Also force the newly
# claimed/spawned ArmorStand entity's internal health to full so vanilla entity
# state cannot leak into or prematurely kill the new pet.
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

# loadPet() restores the same saved pet after a restart and therefore keeps its
# saved health. loadPetSettings(), however, is used when a player claims an
# armor stand / creates a replacement pet. Saved preferences may be reused,
# but mortality state belongs to the old pet and must never transfer.
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
old_load = """\t\tPet pet = Pet.createPet(type, owner, stand);
\t\tpet.deserializeSettings(data);

\t\treturn pet;
"""
new_load = """\t\t// This is a newly created pet instance. Reuse cosmetic/behavior settings,
\t\t// but never inherit health or death state from an earlier pet belonging
\t\t// to the same owner and type.
\t\tdata.mortalDead = false;
\t\tdata.health = 20.0F;
\t\tdata.healthModelVersion = 1;

\t\tPet pet = Pet.createPet(type, owner, stand);
\t\tpet.deserializeSettings(data);
\t\tpet.mortalDead = false;
\t\tpet.health = 20.0F;
\t\tstand.setHealth(20.0F);

\t\treturn pet;
"""
if body.count(old_load) != 1:
    raise SystemExit(
        f"Expected one loadPetSettings deserialize block, found {body.count(old_load)}"
    )
new_body = body.replace(old_load, new_load, 1)
storage = storage[:method_match.start("body")] + new_body + storage[method_match.end("body"):]
storage_path.write_text(storage, encoding="utf-8")

# Build-time invariants: health remains an instance field, restoring a saved
# pet still reads saved health, and only the new-pet settings path forces 20.
pet_check = pet_path.read_text(encoding="utf-8")
storage_check = storage_path.read_text(encoding="utf-8")
if "public static float health" in pet_check:
    raise SystemExit("Pet health must never be static/shared")
if pet_check.count("public float health;") != 1:
    raise SystemExit("Expected exactly one per-Pet health field")
if pet_check.count("this.stand.setHealth(20.0F);") < 1:
    raise SystemExit("Fresh Pet constructor does not initialize entity health")
if storage_check.count("data.health = 20.0F;") != 1:
    raise SystemExit("New-pet settings path must reset saved health exactly once")
if storage_check.count("pet.health = 20.0F;") != 1:
    raise SystemExit("New Pet instance health was not explicitly reset")
if storage_check.count("stand.setHealth(20.0F);") != 1:
    raise SystemExit("New pet ArmorStand entity health was not explicitly reset")

print("Initialized every newly created ArmorStandPet with an independent 20-point health pool")
