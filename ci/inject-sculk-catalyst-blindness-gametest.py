from pathlib import Path
import json
import runpy

# Refine the already-applied production exemption into the explicit predicate that the
# real AREA loop calls. This source change intentionally remains after the temporary
# GameTest class is removed, so the production JAR is built from the verified path.
runpy.run_path('ci/refine-sculk-catalyst-player-blindness-predicate.py', run_name='__main__')

root = Path('project')
modjson = root / 'src/main/resources/fabric.mod.json'
testjava = root / 'src/main/java/com/mcmoddev/golems/test/SculkCatalystBlindnessGameTest.java'

data = json.loads(modjson.read_text())
entries = data.setdefault('entrypoints', {}).setdefault('fabric-gametest', [])
entry = 'com.mcmoddev.golems.test.SculkCatalystBlindnessGameTest'
if entry not in entries:
    entries.append(entry)
modjson.write_text(json.dumps(data, indent=2) + '\n')

testjava.parent.mkdir(parents=True, exist_ok=True)
testjava.write_text(r'''package com.mcmoddev.golems.test;

import com.mcmoddev.golems.data.behavior.EffectBehavior;
import com.mcmoddev.golems.data.behavior.util.TargetedMobEffects;
import com.mcmoddev.golems.entity.GolemBase;
import com.mojang.authlib.GameProfile;
import net.fabricmc.fabric.api.gametest.v1.FabricGameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ClientInformation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.animal.Cow;
import net.minecraft.world.entity.monster.Zombie;

import java.util.UUID;

public final class SculkCatalystBlindnessGameTest implements FabricGameTest {
    private static ServerPlayer detachedPlayer(final GameTestHelper helper, final String name) {
        // Deliberately do NOT add this headless player to level.players() or the world
        // entity manager. It is used only for Player type + identity predicate checks.
        return new ServerPlayer(helper.getLevel().getServer(), helper.getLevel(),
                new GameProfile(UUID.randomUUID(), name), ClientInformation.createDefault());
    }

    private static GolemBase sculkCatalyst(final GameTestHelper helper, final BlockPos pos) {
        final GolemBase g = GolemBase.create(helper.getLevel(),
                ResourceLocation.fromNamespaceAndPath("golems", "sculk_catalyst"));
        helper.assertTrue(g != null, "Failed to create Sculk Catalyst Golem");
        g.moveTo(helper.absolutePos(pos), 0.0F, 0.0F);
        g.setNoGravity(true);
        helper.getLevel().addFreshEntity(g);
        g.finalizeSpawn(helper.getLevel(), helper.getLevel().getCurrentDifficultyAt(g.blockPosition()),
                MobSpawnType.MOB_SUMMONED, null);
        return g;
    }

    private static Zombie zombie(final GameTestHelper helper, final double x, final double y, final double z) {
        final Zombie e = EntityType.ZOMBIE.create(helper.getLevel());
        helper.assertTrue(e != null, "Failed to create Zombie");
        e.moveTo(x, y, z, 0.0F, 0.0F);
        e.setNoAi(true);
        e.setNoGravity(true);
        helper.getLevel().addFreshEntity(e);
        return e;
    }

    private static Cow cow(final GameTestHelper helper, final double x, final double y, final double z) {
        final Cow e = EntityType.COW.create(helper.getLevel());
        helper.assertTrue(e != null, "Failed to create Cow");
        e.moveTo(x, y, z, 0.0F, 0.0F);
        e.setNoAi(true);
        e.setNoGravity(true);
        helper.getLevel().addFreshEntity(e);
        return e;
    }

    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 100)
    public void sculkCatalystAreaBlindnessSkipsPlayerBystandersButHitsDirectPlayer(final GameTestHelper helper) {
        final GolemBase golem = sculkCatalyst(helper, new BlockPos(8, 20, 8));
        final Zombie directMob = zombie(helper, golem.getX() + 1.0D, golem.getY(), golem.getZ());
        final Cow areaMob = cow(helper, golem.getX() + 2.0D, golem.getY(), golem.getZ());

        // Exercise the real attack-triggered behavior and real AREA entity query. Both
        // the struck non-player and a nearby non-player bystander must still be blinded.
        helper.assertTrue(golem.doHurtTarget(directMob), "Sculk Catalyst failed to land direct mob attack");
        helper.assertTrue(directMob.hasEffect(MobEffects.BLINDNESS), "Directly attacked mob did not receive blindness");
        helper.assertTrue(areaMob.hasEffect(MobEffects.BLINDNESS), "Nearby non-player mob lost existing area blindness");

        TargetedMobEffects targeted = null;
        for (var behavior : golem.getContainer().orElseThrow().getBehaviors().getActiveBehaviors(golem)) {
            if (behavior instanceof EffectBehavior effectBehavior) {
                targeted = effectBehavior.getTargetedMobEffects();
                break;
            }
        }
        helper.assertTrue(targeted != null, "Sculk Catalyst blindness EffectBehavior missing");
        helper.assertTrue(targeted.excludeBystanderPlayers(), "Sculk Catalyst did not opt into player-bystander exemption");

        final ServerPlayer directPlayer = detachedPlayer(helper, "SculkDirectPlayer");
        final ServerPlayer bystanderPlayer = detachedPlayer(helper, "SculkBystanderPlayer");

        // Exercise the exact predicate called by the production AREA loop. A player
        // bystander is rejected, the exact directly attacked player is accepted by
        // object identity, a different player remains rejected, and non-player living
        // entities remain accepted.
        helper.assertTrue(!targeted.shouldApplyToAreaTarget(directPlayer, directMob),
                "Player bystander was accepted when a mob was directly attacked");
        helper.assertTrue(targeted.shouldApplyToAreaTarget(directPlayer, directPlayer),
                "The exact directly attacked player was incorrectly exempt");
        helper.assertTrue(!targeted.shouldApplyToAreaTarget(bystanderPlayer, directPlayer),
                "A different nearby player was accepted during direct-player attack");
        helper.assertTrue(targeted.shouldApplyToAreaTarget(areaMob, directPlayer),
                "Non-player AREA target was incorrectly filtered out");
        helper.assertTrue(targeted.shouldApplyToAreaTarget(directMob, directMob),
                "Directly attacked non-player target was incorrectly filtered out");

        golem.discard();
        directMob.discard();
        areaMob.discard();
        helper.succeed();
    }
}
''')
print('Injected robust Sculk Catalyst player-bystander blindness GameTest.')
