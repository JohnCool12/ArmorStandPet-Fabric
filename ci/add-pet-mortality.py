from pathlib import Path
import re

root = Path("project/src/main/java/io/github/kyzderp/armorstandpet")


def insert_after_once(path: Path, marker: str, addition: str, label: str) -> None:
    source = path.read_text(encoding="utf-8")
    if addition.strip() in source:
        return
    if source.count(marker) != 1:
        raise SystemExit(f"Expected one {label} marker in {path}, found {source.count(marker)}")
    source = source.replace(marker, marker + addition, 1)
    path.write_text(source, encoding="utf-8")


# Saved JSON fields. Initializers ensure old files remain invincible with full
# health when these fields are absent.
pet_data = root / "storage/PetData.java"
insert_after_once(
    pet_data,
    "\tpublic boolean combatEnabled;\n",
    "\tpublic boolean invincible = true;\n\tpublic boolean mortalDead;\n\tpublic float health = 20.0F;\n",
    "PetData combat field",
)

# Runtime fields and serialization.
pet_path = root / "types/Pet.java"
insert_after_once(
    pet_path,
    "\tpublic boolean combatEnabled;\n",
    "\tpublic boolean invincible;\n\tpublic boolean mortalDead;\n",
    "Pet combat field",
)
insert_after_once(
    pet_path,
    "\t\tthis.combatEnabled = false;\n",
    "\t\tthis.invincible = true;\n\t\tthis.mortalDead = false;\n",
    "Pet combat default",
)
insert_after_once(
    pet_path,
    "\t\tdata.combatEnabled = this.combatEnabled;\n",
    "\t\tdata.invincible = this.invincible;\n\t\tdata.mortalDead = this.mortalDead;\n"
    "\t\tdata.health = this.stand == null ? 20.0F : this.stand.getHealth();\n",
    "Pet combat serialization",
)
insert_after_once(
    pet_path,
    "\t\tthis.combatEnabled = data.combatEnabled;\n",
    "\t\tthis.invincible = data.invincible;\n\t\tthis.mortalDead = data.mortalDead;\n"
    "\t\tthis.stand.setHealth(this.mortalDead ? 0.0F : Math.max(1.0F, Math.min(20.0F, data.health)));\n"
    "\t\tif (this.mortalDead)\n\t\t\tthis.stand.discard();\n",
    "Pet combat deserialization",
)

# Route entity damage through the optional mortality controller. The existing
# default behavior remains invincible because the controller returns false
# until the saved pet setting is explicitly turned off.
entity_path = root / "entity/PetArmorStandEntity.java"
entity_source = entity_path.read_text(encoding="utf-8")
controller_import = "import io.github.kyzderp.armorstandpet.combat.PetMortalityController;\n"
if controller_import not in entity_source:
    import_marker = "import io.github.kyzderp.armorstandpet.util.ColorUtil;\n"
    if entity_source.count(import_marker) != 1:
        raise SystemExit("Could not find PetArmorStandEntity import marker")
    entity_source = entity_source.replace(import_marker, controller_import + import_marker, 1)

hurt_pattern = re.compile(
    r"(@Override\s+public\s+boolean\s+hurtServer\s*\(\s*ServerLevel\s+world\s*,\s*"
    r"DamageSource\s+source\s*,\s*float\s+amount\s*\)\s*\{)\s*"
    r"return\s+false\s*;\s*(\})",
    re.DOTALL,
)
entity_source, hurt_count = hurt_pattern.subn(
    r"\1\n\t\treturn PetMortalityController.hurt(this, world, source, amount);\n\t\2",
    entity_source,
    count=1,
)
if hurt_count != 1:
    raise SystemExit(f"Expected one invincible hurtServer body, found {hurt_count}")

# Include health-zero state instead of only considering entity removal.
old_dead = "public boolean isDeadOrDying()\n\t{\n\t\treturn this.isRemoved();\n\t}"
new_dead = "public boolean isDeadOrDying()\n\t{\n\t\treturn super.isDeadOrDying() || this.isRemoved();\n\t}"
if entity_source.count(old_dead) != 1:
    raise SystemExit("Could not find PetArmorStandEntity isDeadOrDying method")
entity_source = entity_source.replace(old_dead, new_dead, 1)
entity_path.write_text(entity_source, encoding="utf-8")

# A mortally killed pet must not be recreated by movement, login, or dimension
# restoration code. The mode command is the explicit revival path.
player_listener = root / "listeners/PlayerActionListener.java"
player_source = player_listener.read_text(encoding="utf-8")
pet_lookup = "\t\t\t\tPet pet = OwnerToPet.get(worldname, player.getName().getString());\n\t\t\t\tif (pet == null)\n\t\t\t\t\tcontinue;\n"
pet_guard = pet_lookup + "\n\t\t\t\tif (pet.mortalDead)\n\t\t\t\t\tcontinue;\n"
if player_source.count(pet_lookup) != 1:
    raise SystemExit("Could not find PlayerActionListener pet lookup")
player_source = player_source.replace(pet_lookup, pet_guard, 1)
player_listener.write_text(player_source, encoding="utf-8")

respawn_path = root / "listeners/PetRespawnListener.java"
respawn_source = respawn_path.read_text(encoding="utf-8")
old_spawn_guard = "if (pet == null || !pet.isMobile)"
new_spawn_guard = "if (pet == null || !pet.isMobile || pet.mortalDead)"
if respawn_source.count(old_spawn_guard) != 1:
    raise SystemExit("Could not find PetRespawnListener spawn guard")
respawn_source = respawn_source.replace(old_spawn_guard, new_spawn_guard, 1)

world_lookup = "\t\tPet pet = OwnerToPet.get(fromWorld, player.getName().getString());\n"
world_guard = world_lookup + "\n\t\tif (pet != null && pet.mortalDead)\n\t\t\treturn;\n"
if respawn_source.count(world_lookup) != 1:
    raise SystemExit("Could not find PetRespawnListener world-change lookup")
respawn_source = respawn_source.replace(world_lookup, world_guard, 1)
respawn_path.write_text(respawn_source, encoding="utf-8")

# Register /aspet invincible alongside the existing combat toggle.
dispatcher_path = root / "normalcommands/ASPetCommand.java"
dispatcher = dispatcher_path.read_text(encoding="utf-8")
combat_registration = "\t\tcommands.put(\"combat\", new CombatCommand());\n"
invincible_registration = "\t\tcommands.put(\"invincible\", new InvincibleCommand());\n"
if invincible_registration not in dispatcher:
    if dispatcher.count(combat_registration) != 1:
        raise SystemExit("Could not find combat command registration")
    dispatcher = dispatcher.replace(combat_registration,
            combat_registration + invincible_registration, 1)
dispatcher_path.write_text(dispatcher, encoding="utf-8")

checks = {
    pet_data: ["boolean invincible = true", "boolean mortalDead", "float health = 20.0F"],
    pet_path: ["boolean invincible", "boolean mortalDead", "data.health", "this.stand.setHealth"],
    entity_path: ["PetMortalityController.hurt", "super.isDeadOrDying()"],
    player_listener: ["if (pet.mortalDead)"],
    respawn_path: ["!pet.isMobile || pet.mortalDead", "pet != null && pet.mortalDead"],
    dispatcher_path: ["InvincibleCommand"],
}
for path, required in checks.items():
    text = path.read_text(encoding="utf-8")
    for item in required:
        if item not in text:
            raise SystemExit(f"Mortality integration missing {item!r} in {path}")

print("Added persistent /aspet invincible mode with 20 health and real death state")
