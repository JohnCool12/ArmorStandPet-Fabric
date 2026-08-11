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
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.GameType;
import net.minecraft.world.phys.AABB;

import java.util.List;
import java.util.UUID;

/** CI-only regression test. Deleted before the production JAR is packaged. */
public final class VillageReputationGameTest implements FabricGameTest {
    private static ServerPlayer makeListedSurvivalPlayer(final GameTestHelper helper, final String name) {
        final ServerPlayer player = new ServerPlayer(
                helper.getLevel().getServer(), helper.getLevel(),
                new GameProfile(UUID.randomUUID(), name), ClientInformation.createDefault()) {
            @Override public boolean isCreative() { return false; }
            @Override public boolean isSpectator() { return false; }
            @Override public void tick() { }
            @Override public void doTick() { }
        };
        player.gameMode.changeGameModeForPlayer(GameType.SURVIVAL);
        GameType.SURVIVAL.updatePlayerAbilities(player.getAbilities());
        player.setNoGravity(true);
        helper.getLevel().players().add(player);
        return player;
    }

    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 40)
    public void constructedExtraGolemMatchesVanillaVillageReputation(final GameTestHelper helper) {
        final GolemBase extra = GolemBase.create(helper.getLevel(),
                ResourceLocation.fromNamespaceAndPath(ExtraGolems.MODID, "obsidian"));
        helper.assertTrue(extra != null, "Failed to create Obsidian Extra Golem");
        extra.moveTo(helper.absolutePos(new BlockPos(4, 20, 4)), 0.0F, 0.0F);
        extra.setNoGravity(true);
        extra.markConstructedNeutral();

        final IronGolem vanilla = EntityType.IRON_GOLEM.create(helper.getLevel());
        helper.assertTrue(vanilla != null, "Failed to create vanilla Iron Golem");
        vanilla.moveTo(helper.absolutePos(new BlockPos(44, 20, 4)), 0.0F, 0.0F);
        vanilla.setNoGravity(true);
        vanilla.setPlayerCreated(false);

        final Villager extraVillager = EntityType.VILLAGER.create(helper.getLevel());
        final Villager vanillaVillager = EntityType.VILLAGER.create(helper.getLevel());
        helper.assertTrue(extraVillager != null && vanillaVillager != null, "Failed to create villager controls");
        extraVillager.moveTo(extra.getX(), extra.getY(), extra.getZ() + 1.0D, 0.0F, 0.0F);
        vanillaVillager.moveTo(vanilla.getX(), vanilla.getY(), vanilla.getZ() + 1.0D, 0.0F, 0.0F);
        extraVillager.setNoAi(true); vanillaVillager.setNoAi(true);
        extraVillager.setNoGravity(true); vanillaVillager.setNoGravity(true);
        helper.getLevel().addFreshEntity(extraVillager);
        helper.getLevel().addFreshEntity(vanillaVillager);

        final ServerPlayer extraPlayer = makeListedSurvivalPlayer(helper, "ExtraVillageRep");
        final ServerPlayer vanillaPlayer = makeListedSurvivalPlayer(helper, "VanillaVillageRep");
        extraPlayer.setPos(extra.getX() + 7.0D, extra.getY(), extra.getZ());
        vanillaPlayer.setPos(vanilla.getX() + 7.0D, vanilla.getY(), vanilla.getZ());

        extraVillager.getGossips().add(extraPlayer.getUUID(), GossipType.MAJOR_NEGATIVE, 25);
        vanillaVillager.getGossips().add(vanillaPlayer.getUUID(), GossipType.MAJOR_NEGATIVE, 25);

        final TargetingConditions conditions = TargetingConditions.forCombat().range(64.0D);
        final boolean vanillaVillagerCondition = conditions.test(vanilla, vanillaVillager);
        final boolean extraVillagerCondition = conditions.test(extra, extraVillager);
        final boolean vanillaPlayerCondition = conditions.test(vanilla, vanillaPlayer);
        final boolean extraPlayerCondition = conditions.test(extra, extraPlayer);
        final boolean vanillaLos = vanilla.getSensing().hasLineOfSight(vanillaPlayer);
        final boolean extraLos = extra.getSensing().hasLineOfSight(extraPlayer);
        final double vanillaVisibility = vanillaPlayer.getVisibilityPercent(vanilla);
        final double extraVisibility = extraPlayer.getVisibilityPercent(extra);
        final double vanillaDistance = vanilla.distanceToSqr(vanillaPlayer);
        final double extraDistance = extra.distanceToSqr(extraPlayer);
        final boolean vanillaSeenEnemy = vanillaPlayer.canBeSeenAsEnemy();
        final boolean extraSeenEnemy = extraPlayer.canBeSeenAsEnemy();

        final AABB vanillaBox = vanilla.getBoundingBox().inflate(10.0D, 8.0D, 10.0D);
        final AABB extraBox = extra.getBoundingBox().inflate(10.0D, 8.0D, 10.0D);
        final List<Villager> vanillaVillagers = helper.getLevel().getNearbyEntities(Villager.class, conditions, vanilla, vanillaBox);
        final List<Villager> extraVillagers = helper.getLevel().getNearbyEntities(Villager.class, conditions, extra, extraBox);
        final List<Player> vanillaPlayers = helper.getLevel().getNearbyPlayers(conditions, vanilla, vanillaBox);
        final List<Player> extraPlayers = helper.getLevel().getNearbyPlayers(conditions, extra, extraBox);

        final int vanillaRep = vanillaVillager.getPlayerReputation(vanillaPlayer);
        final int extraRep = extraVillager.getPlayerReputation(extraPlayer);
        final boolean extraPlayerCreated = extra.isPlayerCreated();
        final DefendVillageTargetGoal vanillaGoal = new DefendVillageTargetGoal(vanilla);
        final DefendVillageTargetGoal extraGoal = new DefendVillageTargetGoal(extra);
        final boolean vanillaCanUse = vanillaGoal.canUse();
        final boolean extraCanUse = extraGoal.canUse();
        if (vanillaCanUse) vanillaGoal.start();
        if (extraCanUse) extraGoal.start();
        final boolean vanillaTargetCorrect = vanilla.getTarget() == vanillaPlayer;
        final boolean extraTargetCorrect = extra.getTarget() == extraPlayer;

        final String vanillaDiag = "villagerCondition=" + vanillaVillagerCondition
                + ", playerCondition=" + vanillaPlayerCondition + ", los=" + vanillaLos
                + ", visibility=" + vanillaVisibility + ", distanceSq=" + vanillaDistance
                + ", canBeSeenAsEnemy=" + vanillaSeenEnemy
                + ", nearbyVillagers=" + vanillaVillagers.size() + ", nearbyPlayers=" + vanillaPlayers.size()
                + ", reputation=" + vanillaRep + ", goalCanUse=" + vanillaCanUse
                + ", targetCorrect=" + vanillaTargetCorrect + ", playerCreated=" + vanilla.isPlayerCreated();
        final String extraDiag = "villagerCondition=" + extraVillagerCondition
                + ", playerCondition=" + extraPlayerCondition + ", los=" + extraLos
                + ", visibility=" + extraVisibility + ", distanceSq=" + extraDistance
                + ", canBeSeenAsEnemy=" + extraSeenEnemy
                + ", playerCanAttack=" + extra.canAttack(extraPlayer)
                + ", playerCanAttackType=" + extra.canAttackType(extraPlayer.getType())
                + ", playerAllied=" + extra.isAlliedTo(extraPlayer)
                + ", villagerCanAttack=" + extra.canAttack(extraVillager)
                + ", villagerCanAttackType=" + extra.canAttackType(extraVillager.getType())
                + ", nearbyVillagers=" + extraVillagers.size() + ", nearbyPlayers=" + extraPlayers.size()
                + ", reputation=" + extraRep + ", goalCanUse=" + extraCanUse
                + ", targetCorrect=" + extraTargetCorrect + ", playerCreated=" + extraPlayerCreated;

        helper.getLevel().players().remove(extraPlayer);
        helper.getLevel().players().remove(vanillaPlayer);
        extraVillager.discard(); vanillaVillager.discard();

        helper.assertTrue(vanillaVillagerCondition, "Vanilla villager prerequisite failed; " + vanillaDiag);
        helper.assertTrue(extraVillagerCondition, "Extra villager prerequisite failed; " + extraDiag);
        helper.assertTrue(vanillaPlayerCondition, "Vanilla player prerequisite failed; " + vanillaDiag);
        helper.assertTrue(extraPlayerCondition, "Extra player prerequisite failed; vanilla=" + vanillaDiag + "; extra=" + extraDiag);
        helper.assertTrue(vanillaRep <= -100 && extraRep <= -100, "Reputation setup failed; vanilla=" + vanillaDiag + "; extra=" + extraDiag);
        helper.assertTrue(!extraPlayerCreated, "T-built Extra Golem still PlayerCreated=true; " + extraDiag);
        helper.assertTrue(vanillaCanUse && extraCanUse, "DefendVillageTargetGoal parity failed; vanilla=" + vanillaDiag + "; extra=" + extraDiag);
        helper.assertTrue(vanillaTargetCorrect && extraTargetCorrect, "Low-reputation target selection failed; vanilla=" + vanillaDiag + "; extra=" + extraDiag);
        helper.succeed();
    }
}
''')

print('Injected final TargetingConditions diagnostics for village reputation parity.')
