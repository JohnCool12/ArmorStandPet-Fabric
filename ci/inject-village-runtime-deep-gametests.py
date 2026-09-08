from pathlib import Path
import json

root = Path('project')
modjson = root / 'src/main/resources/fabric.mod.json'
testjava = root / 'src/main/java/com/mcmoddev/golems/test/VillageRuntimeParityGameTest.java'

data = json.loads(modjson.read_text())
entries = data.setdefault('entrypoints', {}).setdefault('fabric-gametest', [])
entry = 'com.mcmoddev.golems.test.VillageRuntimeParityGameTest'
if entry not in entries:
    entries.append(entry)
modjson.write_text(json.dumps(data, indent=2) + '\n')

testjava.parent.mkdir(parents=True, exist_ok=True)
testjava.write_text(r'''package com.mcmoddev.golems.test;

import com.mcmoddev.golems.entity.GolemBase;
import com.mcmoddev.golems.block.GolemHeadBlock;
import com.mojang.authlib.GameProfile;
import net.fabricmc.fabric.api.gametest.v1.FabricGameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ClientInformation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.gossip.GossipType;
import net.minecraft.world.entity.animal.IronGolem;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.AABB;

import java.util.List;
import java.util.UUID;

/** CI-only tests. Production sources restore fabric.mod.json and delete this class. */
public final class VillageRuntimeParityGameTest implements FabricGameTest {
    private static final String NATURAL_TAG = "extra_golems_constructed_true_natural_ai_v1";

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

    private static GolemBase constructFromT(final GameTestHelper helper, final Block material, final BlockPos relativeHead) {
        final BlockPos head = helper.absolutePos(relativeHead);
        helper.getLevel().setBlockAndUpdate(head.below(), material.defaultBlockState());
        helper.getLevel().setBlockAndUpdate(head.below(2), material.defaultBlockState());
        helper.getLevel().setBlockAndUpdate(head.below().east(), material.defaultBlockState());
        helper.getLevel().setBlockAndUpdate(head.below().west(), material.defaultBlockState());
        final boolean spawned = GolemHeadBlock.trySpawnGolem(null, helper.getLevel(), head);
        helper.assertTrue(spawned, "T-shape construction did not spawn an Extra Golem for " + material);
        final List<GolemBase> found = helper.getLevel().getEntitiesOfClass(
                GolemBase.class, new AABB(head).inflate(4.0D), e -> e.isAlive());
        helper.assertTrue(found.size() == 1, "Expected exactly one constructed Extra Golem, found " + found.size());
        final GolemBase golem = found.get(0);
        golem.setNoGravity(true);
        return golem;
    }

    private static Villager addVillager(final GameTestHelper helper, final double x, final double y, final double z) {
        final Villager villager = EntityType.VILLAGER.create(helper.getLevel());
        helper.assertTrue(villager != null, "Failed to create Villager");
        villager.moveTo(x, y, z, 0.0F, 0.0F);
        villager.setNoAi(true);
        villager.setNoGravity(true);
        helper.getLevel().addFreshEntity(villager);
        return villager;
    }

    private static IronGolem addNaturalVanillaControl(final GameTestHelper helper, final double x, final double y, final double z) {
        final IronGolem golem = EntityType.IRON_GOLEM.create(helper.getLevel());
        helper.assertTrue(golem != null, "Failed to create vanilla Iron Golem");
        golem.moveTo(x, y, z, 0.0F, 0.0F);
        golem.setNoGravity(true);
        golem.setPlayerCreated(false);
        helper.getLevel().addFreshEntity(golem);
        return golem;
    }

    private static void tickUntilPlayerTarget(final IronGolem golem, final Player player) {
        for (int i = 0; i < 20 && golem.getTarget() != player; i++) {
            golem.tick();
        }
    }

    private static void cleanupPlayer(final GameTestHelper helper, final ServerPlayer player) {
        helper.getLevel().players().remove(player);
    }

    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 80)
    public void realTConstructedObsidianUsesRuntimeVillageReputation(final GameTestHelper helper) {
        // This uses the actual public T-shape spawning method, including the real ordering:
        // create -> mark constructed -> addFreshEntity -> finalizeSpawn -> onBuilt.
        final GolemBase extra = constructFromT(helper, Blocks.OBSIDIAN, new BlockPos(6, 20, 6));
        helper.assertTrue(!extra.isPlayerCreated(), "Fresh T-built Obsidian ended PlayerCreated=true after finalizeSpawn");
        helper.assertTrue(extra.getTags().contains(NATURAL_TAG), "Fresh T-built Obsidian lacks natural-AI construction marker");

        final IronGolem vanilla = addNaturalVanillaControl(helper, extra.getX() + 40.0D, extra.getY(), extra.getZ());
        final Villager extraVillager = addVillager(helper, extra.getX(), extra.getY(), extra.getZ() + 1.0D);
        final Villager vanillaVillager = addVillager(helper, vanilla.getX(), vanilla.getY(), vanilla.getZ() + 1.0D);
        final ServerPlayer extraPlayer = makeListedSurvivalPlayer(helper, "ExtraFreshRuntimeRep");
        final ServerPlayer vanillaPlayer = makeListedSurvivalPlayer(helper, "VanillaFreshRuntimeRep");
        extraPlayer.setPos(extra.getX() + 7.0D, extra.getY(), extra.getZ());
        vanillaPlayer.setPos(vanilla.getX() + 7.0D, vanilla.getY(), vanilla.getZ());
        extraVillager.getGossips().add(extraPlayer.getUUID(), GossipType.MAJOR_NEGATIVE, 25);
        vanillaVillager.getGossips().add(vanillaPlayer.getUUID(), GossipType.MAJOR_NEGATIVE, 25);
        helper.assertTrue(extraVillager.getPlayerReputation(extraPlayer) <= -100, "Extra reputation setup did not cross vanilla threshold");
        helper.assertTrue(vanillaVillager.getPlayerReputation(vanillaPlayer) <= -100, "Vanilla reputation setup did not cross threshold");

        // Crucially, do NOT instantiate/call DefendVillageTargetGoal ourselves. Tick the
        // real entities so their installed target selectors must schedule the goal.
        tickUntilPlayerTarget(extra, extraPlayer);
        tickUntilPlayerTarget(vanilla, vanillaPlayer);
        final boolean extraTargeted = extra.getTarget() == extraPlayer;
        final boolean vanillaTargeted = vanilla.getTarget() == vanillaPlayer;

        cleanupPlayer(helper, extraPlayer); cleanupPlayer(helper, vanillaPlayer);
        extraVillager.discard(); vanillaVillager.discard(); vanilla.discard(); extra.discard();
        helper.assertTrue(vanillaTargeted, "Vanilla control did not runtime-target its low-reputation player");
        helper.assertTrue(extraTargeted, "REAL T-built Obsidian did not runtime-target its low-reputation player");
        helper.succeed();
    }

    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 80)
    public void realTConstructedBedrockUsesRuntimeVillageReputation(final GameTestHelper helper) {
        final GolemBase bedrock = constructFromT(helper, Blocks.BEDROCK, new BlockPos(6, 20, 6));
        helper.assertTrue(!bedrock.isPlayerCreated(), "Fresh T-built Bedrock ended PlayerCreated=true after finalizeSpawn");
        final Villager villager = addVillager(helper, bedrock.getX(), bedrock.getY(), bedrock.getZ() + 1.0D);
        final ServerPlayer player = makeListedSurvivalPlayer(helper, "BedrockFreshRuntimeRep");
        player.setPos(bedrock.getX() + 7.0D, bedrock.getY(), bedrock.getZ());
        villager.getGossips().add(player.getUUID(), GossipType.MAJOR_NEGATIVE, 25);
        helper.assertTrue(villager.getPlayerReputation(player) <= -100, "Bedrock reputation setup did not cross vanilla threshold");
        tickUntilPlayerTarget(bedrock, player);
        final boolean targeted = bedrock.getTarget() == player;
        cleanupPlayer(helper, player); villager.discard(); bedrock.discard();
        helper.assertTrue(targeted, "REAL T-built Bedrock did not runtime-target its low-reputation player");
        helper.succeed();
    }

    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 80)
    public void legacyPlayerCreatedGolemMigratesOnLoadAndUsesRuntimeReputation(final GameTestHelper helper) {
        // Recreate the exact old-save signature: original T-built Extra Golems had
        // PlayerCreated=true but none of our later construction marker tags.
        final GolemBase legacy = GolemBase.create(helper.getLevel(),
                net.minecraft.resources.ResourceLocation.fromNamespaceAndPath("golems", "obsidian"));
        helper.assertTrue(legacy != null, "Failed to create legacy fixture");
        legacy.setPlayerCreated(true);
        legacy.removeTag(NATURAL_TAG);
        legacy.removeTag("extra_golems_neutral_constructed");
        final CompoundTag saved = new CompoundTag();
        legacy.addAdditionalSaveData(saved);

        final GolemBase loaded = GolemBase.create(helper.getLevel(),
                net.minecraft.resources.ResourceLocation.fromNamespaceAndPath("golems", "obsidian"));
        helper.assertTrue(loaded != null, "Failed to create load fixture");
        loaded.readAdditionalSaveData(saved);
        loaded.moveTo(helper.absolutePos(new BlockPos(6, 20, 6)), 0.0F, 0.0F);
        loaded.setNoGravity(true);
        helper.getLevel().addFreshEntity(loaded);
        helper.assertTrue(!loaded.isPlayerCreated(), "Legacy T-built Extra Golem remained PlayerCreated=true after NBT load");
        helper.assertTrue(loaded.getTags().contains(NATURAL_TAG), "Legacy T-built Extra Golem was not tagged as migrated natural AI");

        final Villager villager = addVillager(helper, loaded.getX(), loaded.getY(), loaded.getZ() + 1.0D);
        final ServerPlayer player = makeListedSurvivalPlayer(helper, "LegacyRuntimeRep");
        player.setPos(loaded.getX() + 7.0D, loaded.getY(), loaded.getZ());
        villager.getGossips().add(player.getUUID(), GossipType.MAJOR_NEGATIVE, 25);
        tickUntilPlayerTarget(loaded, player);
        final boolean targeted = loaded.getTarget() == player;
        cleanupPlayer(helper, player); villager.discard(); loaded.discard(); legacy.discard();
        helper.assertTrue(targeted, "Migrated legacy Extra Golem did not runtime-target its low-reputation player");
        helper.succeed();
    }
}
''')

print('Injected real-construction/runtime-selector/legacy-load village parity GameTests.')
