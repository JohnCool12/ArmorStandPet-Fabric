package com.kyanite.deeperdarker.client;

import com.kyanite.deeperdarker.DeeperDarker;
import com.mojang.blaze3d.vertex.PoseStack;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;

/** Dormant CI-only item-render regression suite. */
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
        int renders = 0;
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
                                renders
                        );
                    } catch (Throwable throwable) {
                        DeeperDarker.LOGGER.error(
                                "DEEPERDARKER_ITEM_RENDER_SMOKE_TEST_FAILED item={} context={} after {} renders",
                                id, context, renders, throwable);
                        throw throwable;
                    } finally {
                        poseStack.popPose();
                    }
                    renders++;
                }
                items++;
            }
            buffers.endBatch();
            DeeperDarker.LOGGER.info(
                    "DEEPERDARKER_ITEM_RENDER_SMOKE_TEST_PASSED items={} contexts={} renders={}",
                    items, CONTEXTS.length, renders);
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
