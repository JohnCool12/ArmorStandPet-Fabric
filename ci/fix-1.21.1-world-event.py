from pathlib import Path
import runpy

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

# This runs before the general 1.21.1 API batch. It marks the distinction
# between restoring the same saved pet and creating a new armor-stand pet;
# the following batch then installs the per-Pet health field used at runtime.
runpy.run_path("ci/initialize-fresh-pet-health.py", run_name="__main__")
