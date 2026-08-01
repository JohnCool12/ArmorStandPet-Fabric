from pathlib import Path

path = Path("project/src/main/java/io/github/kyzderp/armorstandpet/listeners/PetRespawnListener.java")
source = path.read_text(encoding="utf-8")

old_import = "import net.fabricmc.fabric.api.entity.event.v1.ServerEntityLevelChangeEvents;"
new_import = "import net.fabricmc.fabric.api.entity.event.v1.ServerEntityWorldChangeEvents;"
if source.count(old_import) != 1:
    raise SystemExit(f"Expected one 26.2 level-change import, found {source.count(old_import)}")
source = source.replace(old_import, new_import, 1)

old_registration = "ServerEntityLevelChangeEvents.AFTER_PLAYER_CHANGE_LEVEL.register("
new_registration = "ServerEntityWorldChangeEvents.AFTER_PLAYER_CHANGE_WORLD.register("
if source.count(old_registration) != 1:
    raise SystemExit(f"Expected one 26.2 level-change registration, found {source.count(old_registration)}")
source = source.replace(old_registration, new_registration, 1)

if "ServerEntityLevelChangeEvents" in source or "AFTER_PLAYER_CHANGE_LEVEL" in source:
    raise SystemExit("Obsolete 26.2 world-change event remained")

path.write_text(source, encoding="utf-8")
print("Adapted player world-change callback to Fabric 1.21.1 without changing behavior")
