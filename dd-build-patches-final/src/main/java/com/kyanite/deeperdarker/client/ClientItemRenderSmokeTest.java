package com.kyanite.deeperdarker.client;

import com.kyanite.deeperdarker.DeeperDarker;
import com.kyanite.deeperdarker.content.DDBlocks;
import com.kyanite.deeperdarker.content.blocks.CrystallizedAmberBlock;
import com.kyanite.deeperdarker.content.blocks.entity.CrystallizedAmberBlockEntity;
import com.kyanite.deeperdarker.content.blocks.entity.DDHangingSignBlockEntity;
import com.kyanite.deeperdarker.content.blocks.entity.DDSignBlockEntity;
import com.kyanite.deeperdarker.content.blocks.entity.GloomslatePotBlockEntity;
import com.mojang.blaze3d.vertex.PoseStack;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderDispatcher;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;

/** Dormant CI-only client rendering regression suite. */
public final class ClientItemRenderSmokeTest implements ClientModInitializer {
    private static final ItemDisplayContext[] CONTEXTS = {
            ItemDisplayContext.GUI,
            ItemDisplayContext.GROUND,
            ItemDisplayContext.FIXED,
            ItemDisplayContext.HEAD,
            ItemDisplayContext.FIRST_PERSON_LEFT_HAND,
            ItemDisplayContext.FIRST_PERSON_RIGHT_HAND,
            ItemDisplayContext.THIRD_PERSON_LEFT_HAND,
            ItemDisplayContext.THIRD_PERSON_RIGHT_HAND
    };

    private int ticks;
    private boolean finished;

    @Override
    public void onInitializeClient() {
        if (!Boolean.parseBoolean(System.getenv("DEEPERDARKER_ITEM_RENDER_SMOKE_TEST"))) return;
        ClientTickEvents.END_CLIENT_TICK.register(this::tick);
    }

    private void tick(Minecraft client) {
        if (this.finished || ++this.ticks < 100 || client.getOverlay() != null || client.screen == null) return;
        this.finished = true;

        int items = 0;
        int itemRenders = 0;
        int blockRenders = 0;
        int blockEntityRenders = 0;
        PoseStack poseStack = new PoseStack();
        MultiBufferSource.BufferSource buffers = client.renderBuffers().bufferSource();

        try {
            for (Item item : BuiltInRegistries.ITEM) {
                ResourceLocation id = BuiltInRegistries.ITEM.getKey(item);
                if (id == null || !DeeperDarker.MOD_ID.equals(id.getNamespace())) continue;
                ItemStack stack = new ItemStack(item);

                for (ItemDisplayContext context : CONTEXTS) {
                    poseStack.pushPose();
                    try {
                        client.getItemRenderer().renderStatic(
                                stack,
                                context,
                                LightTexture.FULL_BRIGHT,
                                OverlayTexture.NO_OVERLAY,
                                poseStack,
                                buffers,
                                null,
                                itemRenders
                        );
                    } catch (Throwable throwable) {
                        DeeperDarker.LOGGER.error(
                                "DEEPERDARKER_ITEM_RENDER_SMOKE_TEST_FAILED item={} context={} after {} renders",
                                id, context, itemRenders, throwable);
                        throw throwable;
                    } finally {
                        poseStack.popPose();
                    }
                    itemRenders++;
                }
                items++;
            }

            for (Block block : BuiltInRegistries.BLOCK) {
                ResourceLocation id = BuiltInRegistries.BLOCK.getKey(block);
                if (id == null || !DeeperDarker.MOD_ID.equals(id.getNamespace())) continue;
                poseStack.pushPose();
                try {
                    client.getBlockRenderer().renderSingleBlock(
                            block.defaultBlockState(),
                            poseStack,
                            buffers,
                            LightTexture.FULL_BRIGHT,
                            OverlayTexture.NO_OVERLAY
                    );
                } catch (Throwable throwable) {
                    DeeperDarker.LOGGER.error(
                            "DEEPERDARKER_BLOCK_RENDER_SMOKE_TEST_FAILED block={} after {} renders",
                            id, blockRenders, throwable);
                    throw throwable;
                } finally {
                    poseStack.popPose();
                }
                blockRenders++;
            }

            BlockEntityRenderDispatcher dispatcher = client.getBlockEntityRenderDispatcher();
            if (dispatcher == null) throw new IllegalStateException("BlockEntityRenderDispatcher unavailable");

            DDSignBlockEntity sign = new DDSignBlockEntity(BlockPos.ZERO, DDBlocks.ECHO_SIGN.get().defaultBlockState());
            DDHangingSignBlockEntity hangingSign = new DDHangingSignBlockEntity(BlockPos.ZERO, DDBlocks.ECHO_HANGING_SIGN.get().defaultBlockState());
            BlockState amberState = DDBlocks.CRYSTALLIZED_AMBER.get().defaultBlockState()
                    .setValue(CrystallizedAmberBlock.FOSSILIZED, true);
            CrystallizedAmberBlockEntity amber = new CrystallizedAmberBlockEntity(BlockPos.ZERO, amberState);
            GloomslatePotBlockEntity pot = new GloomslatePotBlockEntity(BlockPos.ZERO, DDBlocks.GLOOMSLATE_POT.get().defaultBlockState());

            net.minecraft.world.level.block.entity.BlockEntity[] blockEntities = {sign, hangingSign, amber, pot};
            for (net.minecraft.world.level.block.entity.BlockEntity blockEntity : blockEntities) {
                poseStack.pushPose();
                try {
                    dispatcher.renderItem(
                            blockEntity,
                            poseStack,
                            buffers,
                            LightTexture.FULL_BRIGHT,
                            OverlayTexture.NO_OVERLAY
                    );
                } catch (Throwable throwable) {
                    DeeperDarker.LOGGER.error(
                            "DEEPERDARKER_BLOCK_ENTITY_RENDER_SMOKE_TEST_FAILED class={} after {} renders",
                            blockEntity.getClass().getName(), blockEntityRenders, throwable);
                    throw throwable;
                } finally {
                    poseStack.popPose();
                }
                blockEntityRenders++;
            }

            buffers.endBatch();
            DeeperDarker.LOGGER.info(
                    "DEEPERDARKER_CLIENT_RENDER_SMOKE_TEST_PASSED items={} contexts={} itemRenders={} blockRenders={} blockEntityRenders={}",
                    items, CONTEXTS.length, itemRenders, blockRenders, blockEntityRenders);
            // Keep the legacy marker so the CI gate remains compatible with earlier runs.
            DeeperDarker.LOGGER.info("DEEPERDARKER_ITEM_RENDER_SMOKE_TEST_PASSED items={} contexts={} renders={}",
                    items, CONTEXTS.length, itemRenders);
            client.stop();
        } catch (Throwable throwable) {
            try {
                buffers.endBatch();
            } catch (Throwable ignored) {
            }
            throw throwable;
        }
    }
}
