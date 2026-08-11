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
import com.mojang.authlib.GameProfile;
import net.fabricmc.fabric.api.gametest.v1.FabricGameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ClientInformation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.gossip.GossipType;
import net.minecraft.world.entity.ai.goal.target.DefendVillageTargetGoal;
import net.minecraft.world.entity.ai.targeting.TargetingConditions;
import net.minecraft.world.entity.animal.IronGolem;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.level.GameType;

import java.util.UUID;

/** CI-only regression test. Deleted before the production JAR is packaged. */
public final class VillageReputationGameTest implements FabricGameTest {
    private static ServerPlayer makeListedSurvivalPlayer(final GameTestHelper helper, final String name) {
        final ServerPlayer player = new ServerPlayer(
                helper.getLevel().getServer(),
                helper.getLevel(),
                new GameProfile(UUID.randomUUID(), name),
                ClientInformation.createDefault()) {
            @Override public boolean isCreative() { return false; }
            @Override public boolean isSpectator() { return false; }
            @Override public void tick() { }
            @Override public void doTick() { }
        };
        player.gameMode.changeGameModeForPlayer(GameType.SURVIVAL);
        GameType.SURVIVAL.updatePlayerAbilities(player.getAbilities());
        helper.getLevel().players().add(player);
        return player;
    }

    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 40)
    public void constructedExtraGolemMatchesVanillaVillageReputation(final GameTestHelper helper) {
        final GolemBase extra = GolemBase.create(helper.getLevel(),
                ResourceLocation.fromNamespaceAndPath(ExtraGolems.MODID, "obsidian"));
        helper.assertTrue(extra != null, "Failed to create Obsidian Extra Golem");
        extra.moveTo(helper.absolutePos(new BlockPos(4, 4, 4)), 0.0F, 0.0F);
        extra.markConstructedNeutral();

        final IronGolem vanilla = EntityType.IRON_GOLEM.create(helper.getLevel());
        helper.assertTrue(vanilla != null, "Failed to create vanilla Iron Golem");
        vanilla.moveTo(helper.absolutePos(new BlockPos(44, 4, 4)), 0.0F, 0.0F);
        vanilla.setPlayerCreated(false);

        final Villager extraVillager = EntityType.VILLAGER.create(helper.getLevel());
        final Villager vanillaVillager = EntityType.VILLAGER.create(helper.getLevel());
        helper.assertTrue(extraVillager != null && vanillaVillager != null, "Failed to create villager controls");
        extraVillager.moveTo(extra.getX(), extra.getY(), extra.getZ() + 1.0D, 0.0F, 0.0F);
        vanillaVillager.moveTo(vanilla.getX(), vanilla.getY(), vanilla.getZ() + 1.0D, 0.0F, 0.0F);
        extraVillager.setNoAi(true);
        vanillaVillager.setNoAi(true);
        extraVillager.setNoGravity(true);
        vanillaVillager.setNoGravity(true);
        helper.getLevel().addFreshEntity(extraVillager);
        helper.getLevel().addFreshEntity(vanillaVillager);

        final ServerPlayer extraPlayer = makeListedSurvivalPlayer(helper, "ExtraVillageRep");
        final ServerPlayer vanillaPlayer = makeListedSurvivalPlayer(helper, "VanillaVillageRep");
        extraPlayer.setPos(extra.getX() + 7.0D, extra.getY(), extra.getZ());
        vanillaPlayer.setPos(vanilla.getX() + 7.0D, vanilla.getY(), vanilla.getZ());

        extraVillager.getGossips().add(extraPlayer.getUUID(), GossipType.MAJOR_NEGATIVE, 25);
        vanillaVillager.getGossips().add(vanillaPlayer.getUUID(), GossipType.MAJOR_NEGATIVE, 25);

        helper.assertTrue(extraVillager.getPlayerReputation(extraPlayer) <= -100,
                "Extra-side villager did not receive sufficiently low player reputation");
        helper.assertTrue(vanillaVillager.getPlayerReputation(vanillaPlayer) <= -100,
                "Vanilla-side villager did not receive sufficiently low player reputation");
        helper.assertTrue(!extra.isPlayerCreated(),
                "T-built Extra Golem is still PlayerCreated=true instead of natural-neutral");

        // This is the exact first prerequisite used by vanilla DefendVillageTargetGoal:
        // nearby villagers must pass TargetingConditions.forCombat(). The old Extra
        // Golem canAttackType(VILLAGER)=false override made this assertion fail.
        final TargetingConditions vanillaConditions = TargetingConditions.forCombat().range(64.0D);
        helper.assertTrue(vanillaConditions.test(vanilla, vanillaVillager),
                "Vanilla control villager unexpectedly failed vanilla combat TargetingConditions");
        helper.assertTrue(vanillaConditions.test(extra, extraVillager),
                "Extra Golem still cannot see its villager through vanilla combat TargetingConditions; "
                        + "canAttack=" + extra.canAttack(extraVillager)
                        + ", canAttackType=" + extra.canAttackType(extraVillager.getType())
                        + ", allied=" + extra.isAlliedTo(extraVillager));

        // Invoke the actual vanilla goal synchronously so the headless ServerPlayers never
        // enter unrelated network/physics ticking. Both controls see the same reputation
        // conditions and must select their corresponding low-reputation player.
        final DefendVillageTargetGoal vanillaGoal = new DefendVillageTargetGoal(vanilla);
        final DefendVillageTargetGoal extraGoal = new DefendVillageTargetGoal(extra);
        final boolean vanillaCanUse = vanillaGoal.canUse();
        final boolean extraCanUse = extraGoal.canUse();
        helper.assertTrue(vanillaCanUse, "Vanilla natural Iron Golem DefendVillageTargetGoal did not activate");
        helper.assertTrue(extraCanUse,
                "Extra Golem DefendVillageTargetGoal did not match vanilla at reputation <= -100");

        vanillaGoal.start();
        extraGoal.start();
        helper.assertTrue(vanilla.getTarget() == vanillaPlayer,
                "Vanilla natural Iron Golem did not select its low-reputation player");
        helper.assertTrue(extra.getTarget() == extraPlayer,
                "T-built Extra Golem did not select its low-reputation player like vanilla");

        helper.getLevel().players().remove(extraPlayer);
        helper.getLevel().players().remove(vanillaPlayer);
        extraVillager.discard();
        vanillaVillager.discard();
        helper.succeed();
    }
}
''')

print('Injected synchronous Extra-vs-vanilla village reputation GameTest.')
