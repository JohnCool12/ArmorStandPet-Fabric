from pathlib import Path

root = Path("project/src/main/java/io/github/kyzderp/armorstandpet")


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Expected one {label} in {path}, found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


# HolderLookup.Provider does not exist in the 1.20.1 persistence signatures.
# Remove the parameter cleanly rather than leaving a trailing comma or an
# orphaned registryAccess assignment.
factory = root / "entity/StandFactory.java"
replace_once(
    factory,
    "public static PetArmorStandEntity fromData(ServerLevel world, PetData.StandData data, String owner, String typeKey,\n\t\t\t)",
    "public static PetArmorStandEntity fromData(ServerLevel world, PetData.StandData data, String owner, String typeKey)",
    "StandFactory.fromData provider parameter",
)

storage = root / "storage/PetStorage.java"
replace_once(
    storage,
    "\n\t\t = ASPetMod.getServer().registryAccess();\n",
    "\n",
    "orphaned registry-access assignment",
)
replace_once(
    storage,
    "PetArmorStandEntity stand = StandFactory.fromData(serverWorld, data.stand, owner, type.name(),\n\t\t\t\t);",
    "PetArmorStandEntity stand = StandFactory.fromData(serverWorld, data.stand, owner, type.name());",
    "StandFactory.fromData provider argument",
)

# Guard against the same removal bug appearing elsewhere.
for path in root.rglob("*.java"):
    source = path.read_text(encoding="utf-8")
    if "HolderLookup.Provider" in source or ".registryAccess()" in source:
        raise SystemExit(f"Newer registry-provider API remained in {path}")
    if "\n\t\t = ASPetMod" in source:
        raise SystemExit(f"Orphaned assignment remained in {path}")

print("Cleaned Forge 1.20.1 persistence signatures after provider removal")
