package com.kyanite.deeperdarker.test;

import com.kyanite.deeperdarker.DeeperDarker;
import com.kyanite.deeperdarker.content.DDBlocks;
import com.kyanite.deeperdarker.content.blocks.CrystallizedAmberBlock;
import com.kyanite.deeperdarker.content.blocks.entity.CrystallizedAmberBlockEntity;
import com.kyanite.deeperdarker.content.blocks.entity.GloomslatePotBlockEntity;
import com.kyanite.deeperdarker.world.otherside.OthersideDimension;
import com.kyanite.deeperdarker.world.otherside.OthersideTeleporter;
import java.util.ArrayList;
import java.util.List;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/**
 * CI-only runtime regression suite. Dormant in normal installs.
 */
public final class ServerGameplaySmokeTest implements ModInitializer {
    private static final String ENV = "DEEPERDARKER_GAMEPLAY_SMOKE_TEST";

    @Override
    public void onInitialize() {
        if (!Boolean.parseBoolean(System.getenv(ENV))) return;
        ServerLifecycleEvents.SERVER_STARTED.register(ServerGameplaySmokeTest::run);
    }

    private static void run(MinecraftServer server) {
        try {
            ServerLevel overworld = server.overworld();
            ServerLevel otherside = server.getLevel(OthersideDimension.OTHERSIDE_LEVEL);
            require(otherside != null, "Otherside ServerLevel was not created");

            // Force real chunk generation in multiple Otherside regions, including the
            // coordinates from the reported Crystallized Amber crash.
            for (int x = -2; x <= 2; x++) {
                for (int z = -2; z <= 2; z++) {
                    otherside.getChunk(x, z);
                }
            }
            BlockPos amberPos = new BlockPos(-1328, 57, 1745);
            otherside.getChunk(amberPos);

            // Reproduce the exact runtime path that previously threw because CHEST loot
            // parameters incorrectly included BLOCK_ENTITY.
            BlockState amberState = DDBlocks.CRYSTALLIZED_AMBER.get().defaultBlockState()
                    .setValue(CrystallizedAmberBlock.FOSSILIZED, true);
            otherside.setBlockAndUpdate(amberPos, amberState);
            require(otherside.getBlockEntity(amberPos) instanceof CrystallizedAmberBlockEntity,
                    "Crystallized Amber block entity was not created");
            CrystallizedAmberBlockEntity amber = (CrystallizedAmberBlockEntity) otherside.getBlockEntity(amberPos);
            amber.generateFossil(otherside, amberPos);

            // Exercise custom block-entity state/components independently of rendering.
            BlockPos potPos = amberPos.offset(3, 0, 0);
            otherside.setBlockAndUpdate(potPos, DDBlocks.GLOOMSLATE_POT.get().defaultBlockState());
            require(otherside.getBlockEntity(potPos) instanceof GloomslatePotBlockEntity,
                    "Gloomslate Pot block entity was not created");
            GloomslatePotBlockEntity pot = (GloomslatePotBlockEntity) otherside.getBlockEntity(potPos);
            pot.setTheItem(new ItemStack(Items.DIAMOND, 16));
            require(!pot.getTheItem().isEmpty(), "Gloomslate Pot failed to retain its item");
            require(pot.getUpdateTag(otherside.registryAccess()).contains("item"),
                    "Gloomslate Pot update NBT omitted its item");

            // Exercise the replacement Fabric portal code and its frame construction.
            BlockPos portalOrigin = amberPos.offset(12, 8, 12);
            otherside.setBlockAndUpdate(portalOrigin.below(), Blocks.REINFORCED_DEEPSLATE.defaultBlockState());
            require(OthersideTeleporter.makePortal(otherside, portalOrigin, Direction.Axis.X).isPresent(),
                    "Otherside portal creation failed");

            // Instantiate, add, tick, and remove every custom entity type. This catches
            // missing attributes, bad constructors/synced data, and tick-time assumptions.
            List<String> testedEntities = new ArrayList<>();
            int index = 0;
            for (EntityType<?> type : BuiltInRegistries.ENTITY_TYPE) {
                ResourceLocation id = BuiltInRegistries.ENTITY_TYPE.getKey(type);
                if (id == null || !DeeperDarker.MOD_ID.equals(id.getNamespace())) continue;
                Entity entity = type.create(otherside);
                if (entity == null) continue;
                entity.moveTo(amberPos.getX() + 20.5 + index * 2.0, amberPos.getY() + 2.0,
                        amberPos.getZ() + 20.5, 0.0f, 0.0f);
                require(otherside.addFreshEntity(entity), "Failed to add entity " + id);
                entity.tick();
                testedEntities.add(id.toString());
                entity.discard();
                index++;
            }
            require(!testedEntities.isEmpty(), "No Deeper and Darker entities were tested");

            DeeperDarker.LOGGER.info(
                    "DEEPERDARKER_GAMEPLAY_SMOKE_TEST_PASSED chunks=26 entities={} amber={} pot={} portal=true",
                    testedEntities.size(), amberPos, potPos);
        } catch (Throwable throwable) {
            DeeperDarker.LOGGER.error("DEEPERDARKER_GAMEPLAY_SMOKE_TEST_FAILED", throwable);
            throw throwable;
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException(message);
    }
}
