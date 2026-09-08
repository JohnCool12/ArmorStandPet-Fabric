from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/mixin/VillagerMixin.java')
s = p.read_text()

old = '''\t                Optional<GolemBase> spawned = SpawnUtil.trySpawnMob(\n\t                        EGRegistry.EntityReg.GOLEM.get(), spawnType, level, pos,\n\t                        attempts, spread, yOffset, strategy);\n\t                spawned.ifPresent(golem -> {\n\t                    // SpawnUtil finalizes before we can attach the data-driven id. Reapply\n\t                    // attributes and max health immediately after assigning it.\n\n\t                    golem.setHealth(golem.getMaxHealth());\n\t                });\n\t                return (Optional<T>) (Optional) spawned;\n'''
new = '''\t                Optional<GolemBase> spawned = SpawnUtil.trySpawnMob(\n\t                        EGRegistry.EntityReg.GOLEM.get(), spawnType, level, pos,\n\t                        attempts, spread, yOffset, strategy);\n\n\t                // A replacement roll must never erase vanilla's golem spawn attempt.\n\t                // Only report success when the Extra Golem both entered the world and\n\t                // resolved its selected data-driven material/container correctly.\n\t                if (spawned.isPresent()) {\n\t                    GolemBase golem = spawned.get();\n\t                    if (golem.getGolemId().isPresent() && golem.getContainer().isPresent()) {\n\t                        golem.setHealth(golem.getMaxHealth());\n\t                        return (Optional<T>) (Optional) spawned;\n\t                    }\n\n\t                    // Do not leave a malformed invisible replacement in the world. The\n\t                    // original vanilla SpawnUtil call below gets an immediate clean retry.\n\t                    golem.discard();\n\t                }\n'''
if s.count(old) != 1:
    raise SystemExit(f'Expected one village replacement result block, found {s.count(old)}')
s = s.replace(old, new, 1)

# The final vanilla call must remain after the replacement branch, so an empty/invalid
# replacement falls through to the exact original EntityType.IRON_GOLEM attempt.
needle = 'return SpawnUtil.trySpawnMob(entityType, spawnType, level, pos, attempts, spread, yOffset, strategy);'
if s.count(needle) != 1:
    raise SystemExit('Vanilla SpawnUtil fallback call missing or duplicated')
method_start = s.index('golems$replaceVillageGolem')
method = s[method_start:]
if method.index('if (spawned.isPresent())') > method.index(needle):
    raise SystemExit('Replacement validation appears after vanilla fallback')
if 'golem.discard();' not in method:
    raise SystemExit('Malformed replacement cleanup missing')

p.write_text(s)
print('Applied guaranteed vanilla Iron Golem fallback after failed/invalid Extra Golem village replacement.')
