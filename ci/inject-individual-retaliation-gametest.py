from pathlib import Path
import json

root = Path('project')
modjson = root / 'src/main/resources/fabric.mod.json'
testjava = root / 'src/main/java/com/mcmoddev/golems/test/IndividualRetaliationGameTest.java'

data = json.loads(modjson.read_text())
entries = data.setdefault('entrypoints', {}).setdefault('fabric-gametest', [])
entry = 'com.mcmoddev.golems.test.IndividualRetaliationGameTest'
if entry not in entries:
    entries.append(entry)
modjson.write_text(json.dumps(data, indent=2) + '\n')

testjava.parent.mkdir(parents=True, exist_ok=True)
testjava.write_text(r'''package com.mcmoddev.golems.test;

import com.mcmoddev.golems.block.GolemHeadBlock;
import com.mcmoddev.golems.entity.GolemBase;
import com.mojang.authlib.GameProfile;
import net.fabricmc.fabric.api.gametest.v1.FabricGameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.server.level.ClientInformation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.gossip.GossipType;
import net.minecraft.world.entity.animal.IronGolem;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.AABB;

import java.util.List;
import java.util.UUID;

public final class IndividualRetaliationGameTest implements FabricGameTest {
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

    private static GolemBase construct(final GameTestHelper helper, final Block material, final BlockPos relativeHead) {
        final BlockPos head = helper.absolutePos(relativeHead);
        helper.getLevel().setBlockAndUpdate(head.below(), material.defaultBlockState());
        helper.getLevel().setBlockAndUpdate(head.below(2), material.defaultBlockState());
        helper.getLevel().setBlockAndUpdate(head.below().east(), material.defaultBlockState());
        helper.getLevel().setBlockAndUpdate(head.below().west(), material.defaultBlockState());
        helper.assertTrue(GolemHeadBlock.trySpawnGolem(null, helper.getLevel(), head), "Failed T-build for " + material);
        final List<GolemBase> found = helper.getLevel().getEntitiesOfClass(GolemBase.class,
                new AABB(head).inflate(4.0D), e -> e.isAlive());
        helper.assertTrue(found.size() == 1, "Expected one Extra Golem for " + material + ", found " + found.size());
        final GolemBase g = found.get(0);
        g.setNoGravity(true);
        return g;
    }

    private static IronGolem vanilla(final GameTestHelper helper, final double x, final double y, final double z) {
        final IronGolem g = EntityType.IRON_GOLEM.create(helper.getLevel());
        helper.assertTrue(g != null, "Failed vanilla Iron Golem create");
        g.moveTo(x, y, z, 0.0F, 0.0F);
        g.setNoGravity(true);
        g.setPlayerCreated(false);
        helper.getLevel().addFreshEntity(g);
        return g;
    }

    private static Villager villager(final GameTestHelper helper, final double x, final double y, final double z) {
        final Villager v = EntityType.VILLAGER.create(helper.getLevel());
        helper.assertTrue(v != null, "Failed Villager create");
        v.moveTo(x, y, z, 0.0F, 0.0F);
        v.setNoGravity(true);
        v.setNoAi(true);
        helper.getLevel().addFreshEntity(v);
        return v;
    }

    private static void tick(final IronGolem... golems) {
        for (int i = 0; i < 30; i++) for (IronGolem g : golems) g.tick();
    }

    private static String state(final IronGolem g) {
        return "target=" + (g.getTarget() == null ? "null" : g.getTarget().getName().getString())
                + ", lastHurt=" + (g.getLastHurtByMob() == null ? "null" : g.getLastHurtByMob().getName().getString())
                + ", angerTarget=" + g.getPersistentAngerTarget()
                + ", angerTime=" + g.getRemainingPersistentAngerTime()
                + ", playerCreated=" + g.isPlayerCreated();
    }

    private static void cleanup(final GameTestHelper helper, final ServerPlayer p, final net.minecraft.world.entity.Entity... entities) {
        helper.getLevel().players().remove(p);
        for (var e : entities) e.discard();
    }

    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 100)
    public void directPunchDoesNotAlertBystanderExtraGolem(final GameTestHelper helper) {
        final GolemBase hit = construct(helper, Blocks.OBSIDIAN, new BlockPos(6, 20, 6));
        final GolemBase bystander = construct(helper, Blocks.DIAMOND_BLOCK, new BlockPos(18, 20, 6));
        final ServerPlayer p = player(helper, "ExtraPuncher");
        p.setPos(hit.getX() + 3.0D, hit.getY(), hit.getZ());
        hit.hurt(p.damageSources().playerAttack(p), 1.0F);
        tick(hit, bystander);
        final boolean hitRetaliated = hit.getTarget() == p;
        final boolean bystanderStayedNeutral = bystander.getTarget() != p;
        final String hitState = state(hit), bystanderState = state(bystander);
        cleanup(helper, p, hit, bystander);
        helper.assertTrue(hitRetaliated, "Directly hit Extra Golem failed to retaliate: " + hitState);
        helper.assertTrue(bystanderStayedNeutral, "UNPUNCHED different-material Extra Golem inherited hostility: " + bystanderState);
        helper.succeed();
    }

    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 100)
    public void vanillaNaturalIronGolemDirectPunchIsIndividual(final GameTestHelper helper) {
        final IronGolem hit = vanilla(helper, helper.absolutePos(new BlockPos(6,20,24)).getX(), helper.absolutePos(new BlockPos(6,20,24)).getY(), helper.absolutePos(new BlockPos(6,20,24)).getZ());
        final IronGolem bystander = vanilla(helper, hit.getX() + 12.0D, hit.getY(), hit.getZ());
        final ServerPlayer p = player(helper, "VanillaPuncher");
        p.setPos(hit.getX() + 3.0D, hit.getY(), hit.getZ());
        hit.hurt(p.damageSources().playerAttack(p), 1.0F);
        tick(hit, bystander);
        final boolean hitRetaliated = hit.getTarget() == p;
        final boolean bystanderStayedNeutral = bystander.getTarget() != p;
        final String hitState = state(hit), bystanderState = state(bystander);
        cleanup(helper, p, hit, bystander);
        helper.assertTrue(hitRetaliated, "Directly hit vanilla Iron Golem failed to retaliate: " + hitState);
        helper.assertTrue(bystanderStayedNeutral, "Vanilla unpunched natural Iron Golem inherited hostility: " + bystanderState);
        helper.succeed();
    }

    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 100)
    public void lowVillagerReputationCanMakeMultipleExtraGolemsHostile(final GameTestHelper helper) {
        final GolemBase a = construct(helper, Blocks.OBSIDIAN, new BlockPos(6, 20, 42));
        final GolemBase b = construct(helper, Blocks.DIAMOND_BLOCK, new BlockPos(18, 20, 42));
        final Villager va = villager(helper, a.getX(), a.getY(), a.getZ() + 1.0D);
        final Villager vb = villager(helper, b.getX(), b.getY(), b.getZ() + 1.0D);
        final ServerPlayer p = player(helper, "LowRepPlayer");
        p.setPos(a.getX() + 7.0D, a.getY(), a.getZ());
        va.getGossips().add(p.getUUID(), GossipType.MAJOR_NEGATIVE, 25);
        vb.getGossips().add(p.getUUID(), GossipType.MAJOR_NEGATIVE, 25);
        tick(a, b);
        final boolean both = a.getTarget() == p && b.getTarget() == p;
        final String as = state(a), bs = state(b);
        cleanup(helper, p, a, b, va, vb);
        helper.assertTrue(both, "Legitimate low-reputation village hostility was lost. A=" + as + " B=" + bs);
        helper.succeed();
    }
}
''')
print('Injected individual-retaliation and village-exception GameTests.')
