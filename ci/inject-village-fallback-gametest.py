from pathlib import Path
import json

root = Path('project')
mixin = root / 'src/main/java/com/mcmoddev/golems/mixin/VillagerMixin.java'
modjson = root / 'src/main/resources/fabric.mod.json'
testjava = root / 'src/main/java/com/mcmoddev/golems/test/VillageReplacementFallbackGameTest.java'

# Test-only forcing: guarantee the replacement branch wins and guarantee only the Extra
# Golem SpawnUtil attempt fails (attempts=0). The production vanilla fallback still receives
# the method's original attempts value, so a successful vanilla Iron Golem proves the real
# fallback branch executed after an empty replacement result.
s = mixin.read_text()
old_chance = '        int chance = ExtraGolems.CONFIG.villagerSummonChance();'
new_chance = '        int chance = 100; // GameTest-only forced replacement roll'
if s.count(old_chance) != 1:
    raise SystemExit('VillagerMixin chance anchor missing')
s = s.replace(old_chance, new_chance, 1)

old_id = '            ResourceLocation golemId = EGEvents.getVillagerGolemToSpawn(level, pos, ((Villager) (Object) this).getRandom());'
new_id = '            ResourceLocation golemId = ResourceLocation.fromNamespaceAndPath("golems", "obsidian"); // GameTest-only deterministic material'
if s.count(old_id) != 1:
    raise SystemExit('VillagerMixin golem-id anchor missing')
s = s.replace(old_id, new_id, 1)

old_spawn = '''\t                Optional<GolemBase> spawned = SpawnUtil.trySpawnMob(\n\t                        EGRegistry.EntityReg.GOLEM.get(), spawnType, level, pos,\n\t                        attempts, spread, yOffset, strategy);'''
new_spawn = '''\t                Optional<GolemBase> spawned = SpawnUtil.trySpawnMob(\n\t                        EGRegistry.EntityReg.GOLEM.get(), spawnType, level, pos,\n\t                        0, spread, yOffset, strategy); // GameTest-only forced replacement failure'''
if s.count(old_spawn) != 1:
    raise SystemExit('VillagerMixin Extra SpawnUtil anchor missing')
s = s.replace(old_spawn, new_spawn, 1)
mixin.write_text(s)

data = json.loads(modjson.read_text())
entries = data.setdefault('entrypoints', {}).setdefault('fabric-gametest', [])
entry = 'com.mcmoddev.golems.test.VillageReplacementFallbackGameTest'
if entry not in entries:
    entries.append(entry)
modjson.write_text(json.dumps(data, indent=2) + '\n')

testjava.parent.mkdir(parents=True, exist_ok=True)
testjava.write_text(r'''package com.mcmoddev.golems.test;

import com.mcmoddev.golems.entity.GolemBase;
import net.fabricmc.fabric.api.gametest.v1.FabricGameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.SpawnUtil;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.level.block.Blocks;

import java.lang.reflect.Method;
import java.util.Optional;

public final class VillageReplacementFallbackGameTest implements FabricGameTest {
    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 80)
    public void failedExtraReplacementFallsBackToVanillaIronGolem(final GameTestHelper helper) throws Exception {
        final ServerLevel level = helper.getLevel();
        final BlockPos relativeBase = new BlockPos(8, 6, 8);
        final BlockPos absoluteBase = helper.absolutePos(relativeBase);

        // Give vanilla SpawnUtil a broad, deterministic solid floor and clear headroom.
        for (int x = 3; x <= 13; x++) {
            for (int z = 3; z <= 13; z++) {
                helper.setBlock(new BlockPos(x, 5, z), Blocks.STONE);
                for (int y = 6; y <= 10; y++) {
                    helper.setBlock(new BlockPos(x, y, z), Blocks.AIR);
                }
            }
        }

        final Villager villager = EntityType.VILLAGER.create(level);
        helper.assertTrue(villager != null, "Failed to create test villager");
        villager.moveTo(absoluteBase.getX() + 0.5D, absoluteBase.getY(), absoluteBase.getZ() + 0.5D, 0.0F, 0.0F);
        level.addFreshEntity(villager);

        // The Mixin private redirect is merged directly into Villager at runtime. Calling it
        // here exercises the actual production fallback branch. The test-only source forcing
        // makes the Extra Golem helper receive attempts=0 while the vanilla fallback receives 20.
        final Method redirect = Villager.class.getDeclaredMethod("golems$replaceVillageGolem",
                EntityType.class, MobSpawnType.class, ServerLevel.class, BlockPos.class,
                int.class, int.class, int.class, SpawnUtil.Strategy.class);
        redirect.setAccessible(true);
        final Optional<?> result = (Optional<?>) redirect.invoke(villager,
                EntityType.IRON_GOLEM, MobSpawnType.MOB_SUMMONED, level, absoluteBase,
                20, 2, 4, SpawnUtil.Strategy.IRON_GOLEM);

        helper.assertTrue(result.isPresent(),
                "Failed Extra Golem replacement swallowed the vanilla Iron Golem fallback");
        final Object spawned = result.orElseThrow();
        helper.assertTrue(spawned instanceof Mob, "Fallback result was not a Mob");
        final Mob mob = (Mob) spawned;
        helper.assertTrue(mob.getType() == EntityType.IRON_GOLEM,
                "Fallback produced something other than minecraft:iron_golem: " + mob.getType());
        helper.assertTrue(level.getEntity(mob.getId()) == mob,
                "Fallback Iron Golem was not actually inserted into ServerLevel");

        // The forced Extra attempt had zero tries, so there must not be an Extra Golem left
        // behind while the vanilla fallback succeeds.
        helper.assertTrue(level.getEntitiesOfClass(GolemBase.class,
                mob.getBoundingBox().inflate(16.0D)).isEmpty(),
                "A failed Extra Golem replacement left a phantom Extra Golem in the world");

        mob.discard();
        villager.discard();
        helper.succeed();
    }
}
''')
print('Injected failed-Extra-to-vanilla village fallback GameTest.')
