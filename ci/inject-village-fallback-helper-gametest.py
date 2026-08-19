from pathlib import Path
import json

root = Path('project')
helper_src = root / 'src/main/java/com/mcmoddev/golems/entity/VillageGolemSpawnHelper.java'
modjson = root / 'src/main/resources/fabric.mod.json'
testjava = root / 'src/main/java/com/mcmoddev/golems/test/VillageReplacementFallbackGameTest.java'

# Test-only forcing in the *same production helper* that the Mixin calls:
# - always choose replacement branch
# - deterministic valid Extra material
# - force only Extra SpawnUtil to zero attempts, guaranteeing Optional.empty()
s = helper_src.read_text()
old = '        final int chance = ExtraGolems.CONFIG.villagerSummonChance();'
new = '        final int chance = 100; // GameTest-only forced replacement branch'
if s.count(old) != 1: raise SystemExit('helper chance anchor missing')
s = s.replace(old, new, 1)
old = '            final ResourceLocation golemId = EGEvents.getVillagerGolemToSpawn(level, pos, villager.getRandom());'
new = '            final ResourceLocation golemId = ResourceLocation.fromNamespaceAndPath("golems", "obsidian"); // GameTest-only'
if s.count(old) != 1: raise SystemExit('helper golem id anchor missing')
s = s.replace(old, new, 1)
old = '''                    final Optional<GolemBase> spawned = SpawnUtil.trySpawnMob(\n                            EGRegistry.EntityReg.GOLEM.get(), spawnType, level, pos,\n                            attempts, spread, yOffset, strategy);'''
new = '''                    final Optional<GolemBase> spawned = SpawnUtil.trySpawnMob(\n                            EGRegistry.EntityReg.GOLEM.get(), spawnType, level, pos,\n                            0, spread, yOffset, strategy); // GameTest-only forced Extra failure'''
if s.count(old) != 1: raise SystemExit('helper custom SpawnUtil anchor missing')
s = s.replace(old, new, 1)
helper_src.write_text(s)

data = json.loads(modjson.read_text())
entries = data.setdefault('entrypoints', {}).setdefault('fabric-gametest', [])
entry = 'com.mcmoddev.golems.test.VillageReplacementFallbackGameTest'
if entry not in entries: entries.append(entry)
modjson.write_text(json.dumps(data, indent=2) + '\n')

testjava.parent.mkdir(parents=True, exist_ok=True)
testjava.write_text(r'''package com.mcmoddev.golems.test;

import com.mcmoddev.golems.entity.GolemBase;
import com.mcmoddev.golems.entity.VillageGolemSpawnHelper;
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

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.Optional;

public final class VillageReplacementFallbackGameTest implements FabricGameTest {
    private static SpawnUtil.Strategy ironGolemStrategy() throws Exception {
        SpawnUtil.Strategy first = null;
        for (Field field : SpawnUtil.Strategy.class.getDeclaredFields()) {
            if (!Modifier.isStatic(field.getModifiers()) || !SpawnUtil.Strategy.class.isAssignableFrom(field.getType())) continue;
            field.setAccessible(true);
            SpawnUtil.Strategy value = (SpawnUtil.Strategy) field.get(null);
            if (first == null) first = value;
            if (field.getName().toLowerCase().contains("iron")) return value;
        }
        if (first == null) throw new IllegalStateException("No SpawnUtil.Strategy constants found");
        return first;
    }

    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 80)
    public void failedExtraReplacementFallsBackToVanillaIronGolem(final GameTestHelper helper) throws Exception {
        final ServerLevel level = helper.getLevel();
        final BlockPos relativeBase = new BlockPos(8, 6, 8);
        final BlockPos absoluteBase = helper.absolutePos(relativeBase);

        for (int x = 2; x <= 14; x++) {
            for (int z = 2; z <= 14; z++) {
                helper.setBlock(new BlockPos(x, 5, z), Blocks.STONE);
                for (int y = 6; y <= 11; y++) helper.setBlock(new BlockPos(x, y, z), Blocks.AIR);
            }
        }

        final Villager villager = EntityType.VILLAGER.create(level);
        helper.assertTrue(villager != null, "Failed to create test villager");
        villager.moveTo(absoluteBase.getX() + 0.5D, absoluteBase.getY(), absoluteBase.getZ() + 0.5D, 0.0F, 0.0F);
        level.addFreshEntity(villager);

        // This calls the exact normal production helper used by VillagerMixin. Its test-only
        // forcing makes the Extra attempt receive zero tries; only the unchanged vanilla
        // fallback receives these 20 tries.
        final Optional<? extends Mob> result = VillageGolemSpawnHelper.trySpawn(
                villager, EntityType.IRON_GOLEM, MobSpawnType.MOB_SUMMONED,
                level, absoluteBase, 20, 2, 4, ironGolemStrategy());

        helper.assertTrue(result.isPresent(),
                "Failed Extra replacement swallowed the vanilla Iron Golem spawn attempt");
        final Mob mob = result.orElseThrow();
        helper.assertTrue(mob.getType() == EntityType.IRON_GOLEM,
                "Fallback did not produce minecraft:iron_golem: " + mob.getType());
        helper.assertTrue(level.getEntity(mob.getId()) == mob,
                "Fallback Iron Golem was returned but is not registered in ServerLevel");
        helper.assertTrue(level.getEntitiesOfClass(GolemBase.class,
                mob.getBoundingBox().inflate(16.0D)).isEmpty(),
                "Failed Extra replacement left a phantom Extra Golem behind");

        mob.discard();
        villager.discard();
        helper.succeed();
    }
}
''')
print('Injected direct production-helper failed-Extra-to-vanilla fallback GameTest.')
