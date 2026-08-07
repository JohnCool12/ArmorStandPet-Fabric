package com.kyanite.deeperdarker.content;

import com.kyanite.deeperdarker.DeeperDarker;
import com.kyanite.deeperdarker.content.blocks.entity.*;
import com.kyanite.deeperdarker.util.registry.DDDeferredRegister;
import com.kyanite.deeperdarker.util.registry.DDRegistryEntry;
import net.fabricmc.fabric.api.object.builder.v1.block.entity.FabricBlockEntityTypeBuilder;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.level.block.entity.BlockEntityType;

public class DDBlockEntities {
    public static final DDDeferredRegister<BlockEntityType<?>> BLOCK_ENTITIES =
            DDDeferredRegister.create(Registries.BLOCK_ENTITY_TYPE, DeeperDarker.MOD_ID);

    public static final DDRegistryEntry<BlockEntityType<DDSignBlockEntity>> DEEPER_DARKER_SIGNS =
            BLOCK_ENTITIES.register("deeper_darker_signs", () -> FabricBlockEntityTypeBuilder.create(
                    DDSignBlockEntity::new,
                    DDBlocks.ECHO_SIGN.get(), DDBlocks.ECHO_WALL_SIGN.get(),
                    DDBlocks.BLOOM_SIGN.get(), DDBlocks.BLOOM_WALL_SIGN.get()
            ).build());

    public static final DDRegistryEntry<BlockEntityType<DDHangingSignBlockEntity>> DEEPER_DARKER_HANGING_SIGNS =
            BLOCK_ENTITIES.register("deeper_darker_hanging_signs", () -> FabricBlockEntityTypeBuilder.create(
                    DDHangingSignBlockEntity::new,
                    DDBlocks.ECHO_HANGING_SIGN.get(), DDBlocks.ECHO_WALL_HANGING_SIGN.get(),
                    DDBlocks.BLOOM_HANGING_SIGN.get(), DDBlocks.BLOOM_WALL_HANGING_SIGN.get()
            ).build());

    public static final DDRegistryEntry<BlockEntityType<CrystallizedAmberBlockEntity>> CRYSTALLIZED_AMBER =
            BLOCK_ENTITIES.register("crystallized_amber", () -> FabricBlockEntityTypeBuilder.create(
                    CrystallizedAmberBlockEntity::new, DDBlocks.CRYSTALLIZED_AMBER.get()).build());

    public static final DDRegistryEntry<BlockEntityType<GloomslatePotBlockEntity>> GLOOMSLATE_POT =
            BLOCK_ENTITIES.register("gloomslate_pot", () -> FabricBlockEntityTypeBuilder.create(
                    GloomslatePotBlockEntity::new, DDBlocks.GLOOMSLATE_POT.get()).build());

    public static final DDRegistryEntry<BlockEntityType<SculkJawBlockEntity>> SCULK_JAW =
            BLOCK_ENTITIES.register("sculk_jaw", () -> FabricBlockEntityTypeBuilder.create(
                    SculkJawBlockEntity::new, DDBlocks.SCULK_JAW.get()).build());
}
