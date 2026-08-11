from pathlib import Path
import json

root = Path('project')
modjson = root / 'src/main/resources/fabric.mod.json'
testjava = root / 'src/main/java/com/mcmoddev/golems/test/VillageReputationGameTest.java'

data = json.loads(modjson.read_text())
entry = data.setdefault('entrypoints', {}).setdefault('fabric-gametest', [])
if 'com.mcmoddev.golems.test.VillageReputationGameTest' not in entry:
    entry.append('com.mcmoddev.golems.test.VillageReputationGameTest')
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

/** CI-only parity test; deleted before packaging the production JAR. */
public final class VillageReputationGameTest implements FabricGameTest {
    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 300)
    public void constructedExtraGolemObeysVanillaVillageReputation(final GameTestHelper helper) {
        // DefendVillageTargetGoal discovers candidates through the server level's player list.
        // makeMockPlayer() is only an entity-level mock and is not appropriate for that path;
        // makeMockServerPlayerInLevel() registers the player exactly where vanilla searches.
        final ServerPlayer dislikedPlayer = helper.makeMockServerPlayerInLevel();
        dislikedPlayer.setGameMode(GameType.SURVIVAL);
        dislikedPlayer.setPos(helper.absolutePos(new BlockPos(8, 2, 8)).getCenter());

        final Villager villager = EntityType.VILLAGER.create(helper.getLevel());
        helper.assertTrue(villager != null, "Failed to create villager reputation source");
        villager.moveTo(helper.absolutePos(new BlockPos(8, 2, 5)), 0.0F, 0.0F);
        villager.getGossips().add(dislikedPlayer.getUUID(), GossipType.MAJOR_NEGATIVE, 100);
        helper.getLevel().addFreshEntity(villager);

        final IronGolem vanilla = EntityType.IRON_GOLEM.create(helper.getLevel());
        helper.assertTrue(vanilla != null, "Failed to create vanilla natural Iron Golem control");
        vanilla.moveTo(helper.absolutePos(new BlockPos(4, 2, 5)), 0.0F, 0.0F);
        vanilla.setPlayerCreated(false);
        helper.getLevel().addFreshEntity(vanilla);

        final GolemBase extra = GolemBase.create(helper.getLevel(),
                ResourceLocation.fromNamespaceAndPath(ExtraGolems.MODID, "obsidian"));
        helper.assertTrue(extra != null, "Failed to create Extra Golem");
        extra.moveTo(helper.absolutePos(new BlockPos(12, 2, 5)), 0.0F, 0.0F);
        // This is the exact method invoked by the T-shape + carved-pumpkin construction path.
        extra.markConstructedNeutral();
        helper.getLevel().addFreshEntity(extra);

        helper.runAfterDelay(20, () -> {
            helper.assertTrue(helper.getLevel().players().contains(dislikedPlayer),
                    "Registered ServerPlayer is missing from ServerLevel.players()");
            helper.assertTrue(!dislikedPlayer.isCreative() && !dislikedPlayer.isSpectator(),
                    "Reputation test player is not a valid survival target");
            helper.assertTrue(!vanilla.isPlayerCreated(), "Vanilla control unexpectedly player-created");
            helper.assertTrue(!extra.isPlayerCreated(),
                    "T-built Extra Golem is still player-created and cannot use natural village reputation AI");
            helper.assertTrue(villager.getPlayerReputation(dislikedPlayer) <= -100,
                    "GameTest did not establish sufficiently negative villager reputation: "
                            + villager.getPlayerReputation(dislikedPlayer));
        });

        helper.succeedWhen(() -> {
            // The vanilla control is the oracle. If it cannot see the player, the test setup
            // is invalid and we do NOT claim Extra Golem parity from it.
            helper.assertTrue(vanilla.getTarget() == dislikedPlayer,
                    "Vanilla natural Iron Golem control has not targeted the registered low-reputation ServerPlayer yet; "
                            + "playerListed=" + helper.getLevel().players().contains(dislikedPlayer)
                            + ", reputation=" + villager.getPlayerReputation(dislikedPlayer));
            helper.assertTrue(extra.getTarget() == dislikedPlayer,
                    "T-built Extra Golem failed vanilla village-reputation targeting; currentTarget=" + extra.getTarget());
        });
    }
}
''')
print('Injected registered-ServerPlayer Extra-Golem-vs-vanilla village reputation GameTest.')
