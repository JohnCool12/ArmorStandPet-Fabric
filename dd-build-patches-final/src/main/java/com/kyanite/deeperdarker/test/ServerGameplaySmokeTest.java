package com.kyanite.deeperdarker.test;

import com.kyanite.deeperdarker.DeeperDarker;
import com.kyanite.deeperdarker.content.DDBlocks;
import com.kyanite.deeperdarker.content.DDItems;
import com.kyanite.deeperdarker.content.blocks.CrystallizedAmberBlock;
import com.kyanite.deeperdarker.content.blocks.entity.CrystallizedAmberBlockEntity;
import com.kyanite.deeperdarker.content.blocks.entity.GloomslatePotBlockEntity;
import com.kyanite.deeperdarker.world.otherside.OthersideDimension;
import com.kyanite.deeperdarker.world.otherside.OthersideTeleporter;
import java.util.ArrayList;
import java.util.List;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.entity.event.v1.FabricElytraItem;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/** CI-only runtime regression suite. Dormant in normal installs. */
public final class ServerGameplaySmokeTest implements ModInitializer {
    private static final String ENV = "DEEPERDARKER_GAMEPLAY_SMOKE_TEST";

    @Override
    public void onInitialize() {
        if (!Boolean.parseBoolean(System.getenv(ENV))) return;
        ServerLifecycleEvents.SERVER_STARTED.register(ServerGameplaySmokeTest::run);
    }

    private static void run(MinecraftServer server) {
        try {
            ServerLevel otherside = server.getLevel(OthersideDimension.OTHERSIDE_LEVEL);
            require(otherside != null, "Otherside ServerLevel was not created");

            // Fabric has a dedicated custom-elytra hook. Merely subclassing ElytraItem is
            // not enough for a modded chest item to participate in LivingEntity flight.
            ItemStack soulElytra = new ItemStack(DDItems.SOUL_ELYTRA.get());
            require(soulElytra.getItem() instanceof FabricElytraItem,
                    "Soul Elytra does not implement FabricElytraItem; Fabric flight cannot start");
            LivingEntity elytraProbe = EntityType.ARMOR_STAND.create(otherside);
            require(elytraProbe != null, "Could not create Soul Elytra flight probe entity");
            FabricElytraItem fabricElytra = (FabricElytraItem) soulElytra.getItem();
            require(fabricElytra.useCustomElytra(elytraProbe, soulElytra, false),
                    "Soul Elytra rejected Fabric's custom-elytra flight eligibility check");

            int chunks = 0;
            // Generate two distinct Otherside regions to exercise more biome/feature seeds.
            for (int x = -3; x <= 3; x++) {
                for (int z = -3; z <= 3; z++) {
                    otherside.getChunk(x, z);
                    chunks++;
                }
            }
            int crashChunkX = -1328 >> 4;
            int crashChunkZ = 1745 >> 4;
            for (int x = crashChunkX - 2; x <= crashChunkX + 2; x++) {
                for (int z = crashChunkZ - 2; z <= crashChunkZ + 2; z++) {
                    otherside.getChunk(x, z);
                    chunks++;
                }
            }

            BlockPos amberPos = new BlockPos(-1328, 57, 1745);
            BlockState amberState = DDBlocks.CRYSTALLIZED_AMBER.get().defaultBlockState()
                    .setValue(CrystallizedAmberBlock.FOSSILIZED, true);
            otherside.setBlockAndUpdate(amberPos, amberState);
            require(otherside.getBlockEntity(amberPos) instanceof CrystallizedAmberBlockEntity,
                    "Crystallized Amber block entity was not created");
            CrystallizedAmberBlockEntity amber = (CrystallizedAmberBlockEntity) otherside.getBlockEntity(amberPos);
            amber.generateFossil(otherside, amberPos);

            BlockPos potPos = amberPos.offset(3, 0, 0);
            otherside.setBlockAndUpdate(potPos, DDBlocks.GLOOMSLATE_POT.get().defaultBlockState());
            require(otherside.getBlockEntity(potPos) instanceof GloomslatePotBlockEntity,
                    "Gloomslate Pot block entity was not created");
            GloomslatePotBlockEntity pot = (GloomslatePotBlockEntity) otherside.getBlockEntity(potPos);
            pot.setTheItem(new ItemStack(Items.DIAMOND, 16));
            require(!pot.getTheItem().isEmpty(), "Gloomslate Pot failed to retain its item");
            require(pot.getUpdateTag(otherside.registryAccess()).contains("item"),
                    "Gloomslate Pot update NBT omitted its item");

            BlockPos portalOrigin = amberPos.offset(12, 8, 12);
            otherside.setBlockAndUpdate(portalOrigin.below(), Blocks.REINFORCED_DEEPSLATE.defaultBlockState());
            require(OthersideTeleporter.makePortal(otherside, portalOrigin, Direction.Axis.X).isPresent(),
                    "Otherside portal creation failed");

            // Exercise every registered custom block through vanilla placement/update/shape/removal.
            int testedBlocks = 0;
            BlockPos blockBase = new BlockPos(-1280, 90, 1800);
            for (Block block : BuiltInRegistries.BLOCK) {
                ResourceLocation id = BuiltInRegistries.BLOCK.getKey(block);
                if (id == null || !DeeperDarker.MOD_ID.equals(id.getNamespace())) continue;
                BlockPos pos = blockBase.offset((testedBlocks % 16) * 3, 0, (testedBlocks / 16) * 3);
                otherside.setBlockAndUpdate(pos.below(), Blocks.STONE.defaultBlockState());
                otherside.setBlockAndUpdate(pos, block.defaultBlockState());
                BlockState placed = otherside.getBlockState(pos);
                placed.getShape(otherside, pos);
                placed.getCollisionShape(otherside, pos);
                otherside.removeBlock(pos, false);
                testedBlocks++;
            }
            require(testedBlocks > 0, "No Deeper and Darker blocks were tested");

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
                for (int tick = 0; tick < 5; tick++) entity.tick();
                testedEntities.add(id.toString());
                entity.discard();
                index++;
            }
            require(!testedEntities.isEmpty(), "No Deeper and Darker entities were tested");

            DeeperDarker.LOGGER.info(
                    "DEEPERDARKER_GAMEPLAY_SMOKE_TEST_PASSED chunks={} blocks={} entities={} soulElytra=true amber={} pot={} portal=true",
                    chunks, testedBlocks, testedEntities.size(), amberPos, potPos);
        } catch (Throwable throwable) {
            DeeperDarker.LOGGER.error("DEEPERDARKER_GAMEPLAY_SMOKE_TEST_FAILED", throwable);
            throw throwable;
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException(message);
    }
}
