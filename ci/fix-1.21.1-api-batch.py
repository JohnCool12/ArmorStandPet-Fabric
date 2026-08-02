from pathlib import Path

root = Path("project/src")


def replace_all(path: Path, replacements: list[tuple[str, str]]) -> None:
    source = path.read_text(encoding="utf-8")
    for old, new in replacements:
        if old not in source:
            raise SystemExit(f"Expected compatibility source text not found in {path}: {old!r}")
        source = source.replace(old, new)
    path.write_text(source, encoding="utf-8")


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Expected one {label} in {path}, found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


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
\t\t\t\tpet.getStand().getZ(), Set.of(), admin.getYRot(), admin.getXRot(), false);"""
new_tp = """admin.teleportTo(pet.getStand().serverLevel(), pet.getStand().getX(), pet.getStand().getY(),
\t\t\t\tpet.getStand().getZ(), admin.getYRot(), admin.getXRot());"""
if old_tp not in source:
    raise SystemExit("Expected 26.2 admin teleport overload")
source = source.replace(old_tp, new_tp, 1)
tp.write_text(source, encoding="utf-8")

skull = root / "main/java/io/github/kyzderp/armorstandpet/normalcommands/SkullCommand.java"
replace_all(skull, [
    ("ResolvableProfile.createResolved(p.getGameProfile())",
     "new ResolvableProfile(p.getGameProfile())"),
])

# Keep pet mortality independent from ArmorStand's internal LivingEntity health.
# The custom Pet object owns a real, persisted 20-point pool. This avoids a
# vanilla/custom-entity health mismatch making vulnerable pets die in one hit.
pet_data = root / "main/java/io/github/kyzderp/armorstandpet/storage/PetData.java"
replace_once(
    pet_data,
    "\tpublic float health = 20.0F;\n",
    "\tpublic float health = 20.0F;\n\tpublic int healthModelVersion;\n",
    "PetData health field",
)

pet = root / "main/java/io/github/kyzderp/armorstandpet/types/Pet.java"
replace_once(
    pet,
    "\tpublic boolean mortalDead;\n",
    "\tpublic boolean mortalDead;\n\tpublic float health;\n",
    "Pet mortality fields",
)
replace_once(
    pet,
    "\t\tthis.mortalDead = false;\n",
    "\t\tthis.mortalDead = false;\n\t\tthis.health = 20.0F;\n",
    "Pet mortality defaults",
)
replace_once(
    pet,
    "\t\tdata.health = this.stand == null ? 20.0F : this.stand.getHealth();\n",
    "\t\tdata.health = Math.max(0.0F, Math.min(20.0F, this.health));\n"
    "\t\tdata.healthModelVersion = 1;\n",
    "Pet health serialization",
)
replace_once(
    pet,
    "\t\tthis.stand.setHealth(this.mortalDead ? 0.0F : Math.max(1.0F, Math.min(20.0F, data.health)));\n",
    "\t\tfloat loadedHealth = data.healthModelVersion >= 1 ? data.health : 20.0F;\n"
    "\t\tthis.health = this.mortalDead ? 0.0F : Math.max(1.0F, Math.min(20.0F, loadedHealth));\n"
    "\t\t// Keep the ArmorStand internally alive; Pet.health is authoritative.\n"
    "\t\tthis.stand.setHealth(this.mortalDead ? 0.0F : 20.0F);\n",
    "Pet health deserialization",
)

mortality = root / "main/java/io/github/kyzderp/armorstandpet/combat/PetMortalityController.java"
replace_once(
    mortality,
    "\t\tfloat remaining = Math.max(0.0F, stand.getHealth() - appliedDamage);\n"
    "\t\tstand.setHealth(remaining);\n",
    "\t\tfloat remaining = Math.max(0.0F, pet.health - appliedDamage);\n"
    "\t\tpet.health = remaining;\n"
    "\t\t// Do not let ArmorStand's internal health become the pet's death trigger.\n"
    "\t\tstand.setHealth(MAX_HEALTH);\n",
    "mortality damage subtraction",
)
replace_once(
    mortality,
    "\t\tplayVanillaBreakEffects(level, stand);\n\t\tstand.setHealth(0.0F);\n",
    "\t\tplayVanillaBreakEffects(level, stand);\n\t\tpet.health = 0.0F;\n\t\tstand.setHealth(0.0F);\n",
    "mortality death health reset",
)
replace_once(
    mortality,
    "\t\tNEXT_DAMAGE_TICK.remove(stand.getUUID());\n\t\tstand.setHealth(MAX_HEALTH);\n",
    "\t\tNEXT_DAMAGE_TICK.remove(stand.getUUID());\n\t\tpet.health = MAX_HEALTH;\n\t\tstand.setHealth(MAX_HEALTH);\n",
    "invincibility health reset",
)

invincible_command = root / "main/java/io/github/kyzderp/armorstandpet/normalcommands/InvincibleCommand.java"
replace_once(
    invincible_command,
    "Math.max(0, Math.round(pet.getStand().getHealth()))",
    "Math.max(0, Math.round(pet.health))",
    "invincibility status health source",
)

# Allow the intentional size-aware shadow while continuing to reject the old
# renderer change that removed every ArmorStandPet shadow unconditionally.
renderer = root / "client/java/io/github/kyzderp/armorstandpet/client/PetArmorStandRenderer.java"
renderer_source = renderer.read_text(encoding="utf-8")
if "this.shadowRadius = 0.0F" in renderer_source:
    raise SystemExit("Unexpected all-pet shadow removal in size-aware build")
for marker in [
    "entity.isSmall()",
    "this.normalShadowRadius * SMALL_SHADOW_SCALE",
    ": this.normalShadowRadius",
]:
    if marker not in renderer_source:
        raise SystemExit(f"Size-aware renderer missing {marker!r}")

for forbidden in [".snapTo(", ".showArms()", ".showBasePlate()", ".nameAndId()",
                  "TagParser.create(", "getMinY()", "getMaxY()", "createResolved("]:
    matches = []
    for path in root.rglob("*.java"):
        if forbidden in path.read_text(encoding="utf-8"):
            matches.append(str(path))
    if matches:
        raise SystemExit(f"Obsolete 26.2 API {forbidden!r} remained in: {matches}")

# Guard the health repair itself before compiling.
health_checks = {
    pet_data: ["int healthModelVersion"],
    pet: ["public float health", "data.healthModelVersion = 1", "Pet.health is authoritative"],
    mortality: ["pet.health - appliedDamage", "pet.health = remaining", "pet.health = MAX_HEALTH"],
    invincible_command: ["Math.round(pet.health)"],
}
for path, required in health_checks.items():
    source = path.read_text(encoding="utf-8")
    for marker in required:
        if marker not in source:
            raise SystemExit(f"Health repair missing {marker!r} in {path}")

print("Adapted core 1.21.1 APIs with independent health and size-aware pet shadows")
