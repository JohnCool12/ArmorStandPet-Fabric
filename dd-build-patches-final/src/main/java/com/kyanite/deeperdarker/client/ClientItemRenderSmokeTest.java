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

/**
 * Dormant runtime verification hook. It activates only when the CI environment
 * variable DEEPERDARKER_ITEM_RENDER_SMOKE_TEST is set to true.
 */
public final class ClientItemRenderSmokeTest implements ClientModInitializer {
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

        int rendered = 0;
        PoseStack poseStack = new PoseStack();
        MultiBufferSource.BufferSource buffers = client.renderBuffers().bufferSource();

        try {
            for (Item item : BuiltInRegistries.ITEM) {
                ResourceLocation id = BuiltInRegistries.ITEM.getKey(item);
                if (id == null || !DeeperDarker.MOD_ID.equals(id.getNamespace())) continue;

                poseStack.pushPose();
                try {
                    client.getItemRenderer().renderStatic(
                            new ItemStack(item),
                            ItemDisplayContext.GUI,
                            LightTexture.FULL_BRIGHT,
                            OverlayTexture.NO_OVERLAY,
                            poseStack,
                            buffers,
                            null,
                            rendered
                    );
                } finally {
                    poseStack.popPose();
                }
                rendered++;
            }
            buffers.endBatch();
            DeeperDarker.LOGGER.info("DEEPERDARKER_ITEM_RENDER_SMOKE_TEST_PASSED items={}", rendered);
            client.stop();
        } catch (Throwable throwable) {
            DeeperDarker.LOGGER.error("DEEPERDARKER_ITEM_RENDER_SMOKE_TEST_FAILED after {} items", rendered, throwable);
            throw throwable;
        }
    }
}
