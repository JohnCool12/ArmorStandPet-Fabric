from pathlib import Path
import json

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
import net.minecraft.world.level.GameType;

import java.util.UUID;

public final class SculkCatalystBlindnessGameTest implements FabricGameTest {
    private static ServerPlayer player(final GameTestHelper helper, final String name) {
        final ServerPlayer p = new ServerPlayer(helper.getLevel().getServer(), helper.getLevel(),
                new GameProfile(UUID.randomUUID(), name), ClientInformation.createDefault()) {
            @Override public boolean isCreative() { return false; }
            @Override public boolean isSpectator() { return false; }
            @Override public void tick() { }
            @Override public void doTick() { }
        };
        p.gameMode.changeGameModeForPlayer(GameType.SURVIVAL);
        GameType.SURVIVAL.updatePlayerAbilities(p.getAbilities());
        p.setNoGravity(true);
        helper.getLevel().players().add(p);
        return p;
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
        e.setNoAi(true); e.setNoGravity(true);
        helper.getLevel().addFreshEntity(e);
        return e;
    }

    private static Cow cow(final GameTestHelper helper, final double x, final double y, final double z) {
        final Cow e = EntityType.COW.create(helper.getLevel());
        helper.assertTrue(e != null, "Failed to create Cow");
        e.moveTo(x, y, z, 0.0F, 0.0F);
        e.setNoAi(true); e.setNoGravity(true);
        helper.getLevel().addFreshEntity(e);
        return e;
    }

    private static void cleanup(final GameTestHelper helper, final ServerPlayer a, final ServerPlayer b,
                                final net.minecraft.world.entity.Entity... entities) {
        helper.getLevel().players().remove(a);
        helper.getLevel().players().remove(b);
        for (var e : entities) e.discard();
    }

    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 100)
    public void sculkCatalystAreaBlindnessSkipsPlayerBystandersButHitsDirectPlayer(final GameTestHelper helper) {
        final GolemBase golem = sculkCatalyst(helper, new BlockPos(8, 20, 8));
        final Zombie directMob = zombie(helper, golem.getX() + 1.0D, golem.getY(), golem.getZ());
        final Cow areaMob = cow(helper, golem.getX() + 2.0D, golem.getY(), golem.getZ());
        final ServerPlayer directPlayer = player(helper, "SculkDirectPlayer");
        final ServerPlayer bystanderPlayer = player(helper, "SculkBystanderPlayer");
        directPlayer.setPos(golem.getX() + 3.0D, golem.getY(), golem.getZ());
        bystanderPlayer.setPos(golem.getX() + 4.0D, golem.getY(), golem.getZ());

        // Attack a mob first. Existing AoE blindness must remain for nearby non-player
        // living entities, while both nearby players are only bystanders and stay clear.
        helper.assertTrue(golem.doHurtTarget(directMob), "Sculk Catalyst failed to land direct mob attack");
        helper.assertTrue(directMob.hasEffect(MobEffects.BLINDNESS), "Directly attacked mob did not receive blindness");
        helper.assertTrue(areaMob.hasEffect(MobEffects.BLINDNESS), "Nearby non-player mob lost existing area blindness");
        helper.assertTrue(!directPlayer.hasEffect(MobEffects.BLINDNESS), "Player bystander received blindness during mob attack");
        helper.assertTrue(!bystanderPlayer.hasEffect(MobEffects.BLINDNESS), "Second player bystander received blindness during mob attack");

        directMob.removeAllEffects();
        areaMob.removeAllEffects();
        directPlayer.removeAllEffects();
        bystanderPlayer.removeAllEffects();

        // A headless ServerPlayer cannot be damaged normally by doHurtTarget because it
        // has no real network connection. Dispatch the exact post-success onAttack hook
        // that GolemBase.doHurtTarget invokes after a real melee hit, explicitly passing
        // this player as the direct attack target. This tests the direct-target exception
        // without conflating it with fake-player damage validity.
        golem.getContainer().ifPresent(container -> container.getBehaviors().getActiveBehaviors(golem)
                .forEach(b -> b.onAttack(golem, directPlayer)));
        helper.assertTrue(directPlayer.hasEffect(MobEffects.BLINDNESS), "Directly attacked player was incorrectly exempt from blindness");
        helper.assertTrue(!bystanderPlayer.hasEffect(MobEffects.BLINDNESS), "Nearby non-target player received blindness during player attack");
        helper.assertTrue(areaMob.hasEffect(MobEffects.BLINDNESS), "Nearby non-player mob should still receive area blindness during player attack");

        cleanup(helper, directPlayer, bystanderPlayer, golem, directMob, areaMob);
        helper.succeed();
    }
}
''')
print('Injected Sculk Catalyst player-bystander blindness GameTest.')
