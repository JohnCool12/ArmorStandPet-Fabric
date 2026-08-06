package com.kyanite.deeperdarker.client.render;

import com.kyanite.deeperdarker.content.DDBlocks;
import com.kyanite.deeperdarker.content.blocks.entity.GloomslatePotBlockEntity;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.geom.EntityModelSet;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderDispatcher;
import net.minecraft.core.BlockPos;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;

@SuppressWarnings("NullableProblems")
public class GloomslatePotWithoutLevelRenderer extends BlockEntityWithoutLevelRenderer {
    public GloomslatePotWithoutLevelRenderer(BlockEntityRenderDispatcher blockEntityRenderDispatcher, EntityModelSet entityModelSet) {
        super(blockEntityRenderDispatcher, entityModelSet);
    }

    @Override
    public void renderByItem(ItemStack stack, ItemDisplayContext displayContext, PoseStack poseStack, MultiBufferSource buffer, int packedLight, int packedOverlay) {
        if (!stack.is(DDBlocks.GLOOMSLATE_POT_ITEM.get())) return;

        // The renderer is registered during ClientModInitializer, before Minecraft has
        // necessarily constructed its render dispatchers. Never retain those early values.
        BlockEntityRenderDispatcher dispatcher = Minecraft.getInstance().getBlockEntityRenderDispatcher();
        if (dispatcher == null) return;

        GloomslatePotBlockEntity pot = new GloomslatePotBlockEntity(
                BlockPos.ZERO,
                DDBlocks.GLOOMSLATE_POT.get().defaultBlockState()
        );
        pot.setFromItem(stack);
        dispatcher.renderItem(pot, poseStack, buffer, packedLight, packedOverlay);
    }
}
