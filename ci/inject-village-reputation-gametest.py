from pathlib import Path
import json

root = Path('project')
modjson = root / 'src/main/resources/fabric.mod.json'
testjava = root / 'src/main/java/com/mcmoddev/golems/test/VillageReputationGameTest.java'

data = json.loads(modjson.read_text())
entries = data.setdefault('entrypoints', {}).setdefault('fabric-gametest', [])
if 'com.mcmoddev.golems.test.VillageReputationGameTest' not in entries:
    entries.append('com.mcmoddev.golems.test.VillageReputationGameTest')
modjson.write_text(json.dumps(data, indent=2) + '\n')

testjava.parent.mkdir(parents=True, exist_ok=True)
testjava.write_text(r'''package com.mcmoddev.golems.test;

import com.mcmoddev.golems.ExtraGolems;
import com.mcmoddev.golems.entity.GolemBase;
import net.fabricmc.fabric.api.gametest.v1.FabricGameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.gossip.GossipType;
import net.minecraft.world.entity.animal.IronGolem;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.level.GameType;

/** CI-only regression test. Deleted before the production JAR is packaged. */
public final class VillageReputationGameTest implements FabricGameTest {
    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 240)
    public void constructedExtraGolemMatchesVanillaVillageReputation(final GameTestHelper helper) {
        final GolemBase extra = GolemBase.create(helper.getLevel(),
                ResourceLocation.fromNamespaceAndPath(ExtraGolems.MODID, "obsidian"));
        helper.assertTrue(extra != null, "Failed to create Obsidian Extra Golem");
        extra.moveTo(helper.absolutePos(new BlockPos(4, 2, 4)), 0.0F, 0.0F);
        extra.markConstructedNeutral();
        helper.getLevel().addFreshEntity(extra);

        final IronGolem vanilla = EntityType.IRON_GOLEM.create(helper.getLevel());
        helper.assertTrue(vanilla != null, "Failed to create vanilla Iron Golem");
        vanilla.moveTo(helper.absolutePos(new BlockPos(44, 2, 4)), 0.0F, 0.0F);
        vanilla.setPlayerCreated(false);
        helper.getLevel().addFreshEntity(vanilla);

        final Villager extraVillager = EntityType.VILLAGER.create(helper.getLevel());
        final Villager vanillaVillager = EntityType.VILLAGER.create(helper.getLevel());
        helper.assertTrue(extraVillager != null && vanillaVillager != null, "Failed to create villager controls");
        extraVillager.moveTo(extra.getX() + 2.0D, extra.getY(), extra.getZ(), 0.0F, 0.0F);
        vanillaVillager.moveTo(vanilla.getX() + 2.0D, vanilla.getY(), vanilla.getZ(), 0.0F, 0.0F);
        helper.getLevel().addFreshEntity(extraVillager);
        helper.getLevel().addFreshEntity(vanillaVillager);

        // DefendVillageTargetGoal queries the real ServerLevel player list. Use registered
        // ServerPlayers, then explicitly drive their public server interaction managers
        // into Survival. This is stronger than the helper's synthetic setGameMode path.
        final ServerPlayer extraPlayer = helper.makeMockServerPlayerInLevel();
        final ServerPlayer vanillaPlayer = helper.makeMockServerPlayerInLevel();
        extraPlayer.gameMode.changeGameModeForPlayer(GameType.SURVIVAL);
        vanillaPlayer.gameMode.changeGameModeForPlayer(GameType.SURVIVAL);
        extraPlayer.getAbilities().invulnerable = false;
        extraPlayer.getAbilities().instabuild = false;
        extraPlayer.getAbilities().mayfly = false;
        extraPlayer.getAbilities().flying = false;
        vanillaPlayer.getAbilities().invulnerable = false;
        vanillaPlayer.getAbilities().instabuild = false;
        vanillaPlayer.getAbilities().mayfly = false;
        vanillaPlayer.getAbilities().flying = false;
        extraPlayer.onUpdateAbilities();
        vanillaPlayer.onUpdateAbilities();
        extraPlayer.setPos(extra.getX() + 7.0D, extra.getY(), extra.getZ());
        vanillaPlayer.setPos(vanilla.getX() + 7.0D, vanilla.getY(), vanilla.getZ());
        extraPlayer.setAbsorptionAmount(100.0F);
        vanillaPlayer.setAbsorptionAmount(100.0F);

        // Deterministically create strongly-negative gossip read by vanilla's
        // DefendVillageTargetGoal. The assertions below verify the effective reputation.
        extraVillager.getGossips().add(extraPlayer.getUUID(), GossipType.MAJOR_NEGATIVE, 25);
        vanillaVillager.getGossips().add(vanillaPlayer.getUUID(), GossipType.MAJOR_NEGATIVE, 25);

        helper.assertTrue(extraVillager.getPlayerReputation(extraPlayer) <= -100,
                "Extra-side villager did not receive sufficiently low player reputation");
        helper.assertTrue(vanillaVillager.getPlayerReputation(vanillaPlayer) <= -100,
                "Vanilla-side villager did not receive sufficiently low player reputation");
        helper.assertTrue(!extra.isPlayerCreated(),
                "T-built Extra Golem is still PlayerCreated=true instead of natural-neutral");
        helper.assertTrue(extraPlayer.gameMode.getGameModeForPlayer() == GameType.SURVIVAL
                        && vanillaPlayer.gameMode.getGameModeForPlayer() == GameType.SURVIVAL,
                "Server-player interaction managers are not actually Survival");
        helper.assertTrue(!extraPlayer.isCreative() && !vanillaPlayer.isCreative(),
                "Server-player controls are still Creative and invalid village-defense targets");

        helper.succeedWhen(() -> {
            helper.assertTrue(vanilla.getTarget() == vanillaPlayer,
                    "Vanilla natural Iron Golem has not targeted the very-low-reputation player yet; target=" + vanilla.getTarget());
            helper.assertTrue(extra.getTarget() == extraPlayer,
                    "T-built Extra Golem failed vanilla village-reputation hostility; target=" + extra.getTarget());
        });
    }
}
''')

print('Injected Extra-Golem-vs-vanilla village reputation GameTest with true Survival ServerPlayers.')
