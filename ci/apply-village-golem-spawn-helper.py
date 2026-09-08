from pathlib import Path

root = Path('project')
mixin_path = root / 'src/main/java/com/mcmoddev/golems/mixin/VillagerMixin.java'
helper_path = root / 'src/main/java/com/mcmoddev/golems/entity/VillageGolemSpawnHelper.java'

mixin = mixin_path.read_text()

# Put the full redirect logic in a normal production class. This avoids making correctness
# depend on Mixin-generated method names and gives tests a directly callable code path.
helper_path.parent.mkdir(parents=True, exist_ok=True)
helper_path.write_text(r'''package com.mcmoddev.golems.entity;

import com.mcmoddev.golems.EGEvents;
import com.mcmoddev.golems.EGRegistry;
import com.mcmoddev.golems.ExtraGolems;
import net.minecraft.core.BlockPos;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.SpawnUtil;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.npc.Villager;

import java.util.Optional;

/**
 * Owns village Iron Golem replacement logic. A valid Extra Golem may replace vanilla,
 * but a failed or malformed replacement must never consume the village's vanilla spawn
 * attempt. The exact original vanilla SpawnUtil call is used as the fallback.
 */
public final class VillageGolemSpawnHelper {
    private VillageGolemSpawnHelper() {}

    @SuppressWarnings({"unchecked", "rawtypes"})
    public static <T extends Mob> Optional<T> trySpawn(
            final Villager villager,
            final EntityType<T> entityType,
            final MobSpawnType spawnType,
            final ServerLevel level,
            final BlockPos pos,
            final int attempts,
            final int spread,
            final int yOffset,
            final SpawnUtil.Strategy strategy) {

        final int chance = ExtraGolems.CONFIG.villagerSummonChance();
        if (entityType.equals(EntityType.IRON_GOLEM)
                && spawnType == MobSpawnType.MOB_SUMMONED
                && chance > 0
                && villager.getRandom().nextInt(100) < chance) {
            final ResourceLocation golemId = EGEvents.getVillagerGolemToSpawn(level, pos, villager.getRandom());
            if (golemId != null) {
                GolemBase.beginVillageSummonInitialization(golemId);
                try {
                    final Optional<GolemBase> spawned = SpawnUtil.trySpawnMob(
                            EGRegistry.EntityReg.GOLEM.get(), spawnType, level, pos,
                            attempts, spread, yOffset, strategy);

                    if (spawned.isPresent()) {
                        final GolemBase golem = spawned.get();
                        if (golem.getGolemId().isPresent() && golem.getContainer().isPresent()) {
                            golem.setHealth(golem.getMaxHealth());
                            return (Optional<T>) (Optional) spawned;
                        }

                        // Never leave a malformed/renderer-empty replacement in the level.
                        golem.discard();
                    }
                } finally {
                    GolemBase.endVillageSummonInitialization();
                }
            }
        }

        // Crucial invariant: an unsuccessful replacement attempt falls back to the exact
        // vanilla entity type and original SpawnUtil parameters instead of returning empty.
        return SpawnUtil.trySpawnMob(entityType, spawnType, level, pos,
                attempts, spread, yOffset, strategy);
    }
}
''')

# Make the Mixin redirect a thin delegate. Locate its method by signature and replace its body.
signature = '    private <T extends Mob> Optional<T> golems$replaceVillageGolem('
start = mixin.find(signature)
if start < 0:
    raise SystemExit('VillagerMixin redirect signature missing')
brace = mixin.find('{', start)
if brace < 0:
    raise SystemExit('VillagerMixin redirect opening brace missing')
depth = 0
end = None
for i in range(brace, len(mixin)):
    if mixin[i] == '{':
        depth += 1
    elif mixin[i] == '}':
        depth -= 1
        if depth == 0:
            end = i + 1
            break
if end is None:
    raise SystemExit('VillagerMixin redirect closing brace missing')

old_header = mixin[start:brace + 1]
new_body = '''\n        return com.mcmoddev.golems.entity.VillageGolemSpawnHelper.trySpawn(\n                (Villager) (Object) this, entityType, spawnType, level, pos,\n                attempts, spread, yOffset, strategy);\n    }'''
mixin = mixin[:start] + old_header + new_body + mixin[end:]

# Strong invariants: the redirect has exactly one delegate and no direct custom SpawnUtil logic.
method_start = mixin.find(signature)
method_brace = mixin.find('{', method_start)
depth = 0
method_end = None
for i in range(method_brace, len(mixin)):
    if mixin[i] == '{': depth += 1
    elif mixin[i] == '}':
        depth -= 1
        if depth == 0:
            method_end = i + 1
            break
method = mixin[method_start:method_end]
if method.count('VillageGolemSpawnHelper.trySpawn') != 1:
    raise SystemExit('VillagerMixin redirect does not delegate exactly once')
if 'SpawnUtil.trySpawnMob' in method:
    raise SystemExit('VillagerMixin still contains direct SpawnUtil logic after helper extraction')

mixin_path.write_text(mixin)
print('Extracted village golem replacement/fallback into directly testable production helper.')
