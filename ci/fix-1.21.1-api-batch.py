from pathlib import Path

root = Path("project/src")


def replace_all(path: Path, replacements: list[tuple[str, str]]) -> None:
    source = path.read_text(encoding="utf-8")
    for old, new in replacements:
        if old not in source:
            raise SystemExit(f"Expected compatibility source text not found in {path}: {old!r}")
        source = source.replace(old, new)
    path.write_text(source, encoding="utf-8")


entity = root / "main/java/io/github/kyzderp/armorstandpet/entity/PetArmorStandEntity.java"
replace_all(entity, [
    ("\tprotected void addAdditionalSaveData(CompoundTag tag)",
     "\tpublic void addAdditionalSaveData(CompoundTag tag)"),
    ("\tprotected void readAdditionalSaveData(CompoundTag tag)",
     "\tpublic void readAdditionalSaveData(CompoundTag tag)"),
    ("return this.showArms();", "return this.isShowArms();"),
    ("return this.showBasePlate();", "return !this.isNoBasePlate();"),
])

rotations = root / "main/java/io/github/kyzderp/armorstandpet/util/EulerAngle.java"
replace_all(rotations, [
    ("r.x()", "r.getX()"),
    ("r.y()", "r.getY()"),
    ("r.z()", "r.getZ()"),
])

# The 26.2 positioning helper is named moveTo in 1.21.1 with the same
# coordinates, yaw, and pitch semantics.
for path in [
    root / "main/java/io/github/kyzderp/armorstandpet/entity/StandFactory.java",
    root / "main/java/io/github/kyzderp/armorstandpet/types/Pet.java",
]:
    source = path.read_text(encoding="utf-8")
    if ".snapTo(" not in source:
        raise SystemExit(f"Expected snapTo calls in {path}")
    source = source.replace(".snapTo(", ".moveTo(")
    path.write_text(source, encoding="utf-8")

factory = root / "main/java/io/github/kyzderp/armorstandpet/entity/StandFactory.java"
replace_all(factory, [
    ("existing.showArms()", "existing.isShowArms()"),
    ("existing.showBasePlate()", "!existing.isNoBasePlate()"),
])

storage = root / "main/java/io/github/kyzderp/armorstandpet/storage/PetStorage.java"
replace_all(storage, [
    ("stand.showArms()", "stand.isShowArms()"),
    ("other.showArms()", "other.isShowArms()"),
    ("stand.showBasePlate()", "!stand.isNoBasePlate()"),
    ("other.showBasePlate()", "!other.isNoBasePlate()"),
])

astar = root / "main/java/io/github/kyzderp/armorstandpet/ai/algorithms/AStar.java"
replace_all(astar, [
    ("world.getMinY()", "world.getMinBuildHeight()"),
    ("world.getMaxY()", "world.getMaxBuildHeight()"),
])

permission = root / "main/java/io/github/kyzderp/armorstandpet/util/PermissionUtil.java"
replace_all(permission, [
    ("return player == null || source.getServer().getPlayerList().isOp(player.nameAndId());",
     "return player == null || source.hasPermission(4);"),
])

item_json = root / "main/java/io/github/kyzderp/armorstandpet/util/ItemStackJson.java"
replace_all(item_json, [
    ("Tag nbt = TagParser.create(NbtOps.INSTANCE).parseFully(encoded);",
     "Tag nbt = TagParser.parseTag(encoded);"),
])

gui = root / "main/java/io/github/kyzderp/armorstandpet/gui/ChooseTypeScreenHandler.java"
replace_all(gui, [
    ("StandFactory.claimFrom(this.player.level(), this.rawStand,",
     "StandFactory.claimFrom(this.player.serverLevel(), this.rawStand,"),
])

tp = root / "main/java/io/github/kyzderp/armorstandpet/admincommands/TpCommand.java"
source = tp.read_text(encoding="utf-8")
source = source.replace("import java.util.Set;\n", "")
old_tp = """admin.teleportTo(pet.getStand().serverLevel(), pet.getStand().getX(), pet.getStand().getY(),
				pet.getStand().getZ(), Set.of(), admin.getYRot(), admin.getXRot(), false);"""
new_tp = """admin.teleportTo(pet.getStand().serverLevel(), pet.getStand().getX(), pet.getStand().getY(),
				pet.getStand().getZ(), admin.getYRot(), admin.getXRot());"""
if old_tp not in source:
    raise SystemExit("Expected 26.2 admin teleport overload")
source = source.replace(old_tp, new_tp, 1)
tp.write_text(source, encoding="utf-8")

skull = root / "main/java/io/github/kyzderp/armorstandpet/normalcommands/SkullCommand.java"
replace_all(skull, [
    ("ResolvableProfile.createResolved(p.getGameProfile())",
     "new ResolvableProfile(p.getGameProfile())"),
])

# The ground shadow belongs to the client renderer rather than the entity.
# Set it to zero only for the custom ArmorStandPet renderer so ordinary
# Minecraft armor stands retain their normal rendering behavior.
renderer = root / "client/java/io/github/kyzderp/armorstandpet/client/PetArmorStandRenderer.java"
replace_all(renderer, [
    ("\t\tsuper(context);\n",
     "\t\tsuper(context);\n"
     "\t\tthis.shadowRadius = 0.0F;\n"),
])
renderer_source = renderer.read_text(encoding="utf-8")
if renderer_source.count("this.shadowRadius = 0.0F;") != 1:
    raise SystemExit("ArmorStandPet shadow suppression was not applied exactly once")

for forbidden in [".snapTo(", ".showArms()", ".showBasePlate()", ".nameAndId()",
                  "TagParser.create(", "getMinY()", "getMaxY()", "createResolved("]:
    matches = []
    for path in root.rglob("*.java"):
        if forbidden in path.read_text(encoding="utf-8"):
            matches.append(str(path))
    if matches:
        raise SystemExit(f"Obsolete 26.2 API {forbidden!r} remained in: {matches}")

print("Adapted core 1.21.1 APIs and removed the ArmorStandPet renderer shadow")
