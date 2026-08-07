package com.kyanite.deeperdarker.content.blocks.entity;

import com.kyanite.deeperdarker.content.DDBlockEntities;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.SignBlockEntity;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Fabric-safe hanging sign entity.
 *
 * Vanilla 1.21.1 HangingSignBlockEntity hard-wires BlockEntityType.HANGING_SIGN in
 * its only constructor, which rejects modded hanging-sign blocks during BlockEntity
 * validation. The NeoForge runtime patches this behavior, but Fabric does not. Use
 * the public typed SignBlockEntity constructor and preserve vanilla hanging-sign text
 * dimensions instead.
 */
public class DDHangingSignBlockEntity extends SignBlockEntity {
    public DDHangingSignBlockEntity(BlockPos pos, BlockState blockState) {
        super(DDBlockEntities.DEEPER_DARKER_HANGING_SIGNS.get(), pos, blockState);
    }

    @Override
    public int getTextLineHeight() {
        return 9;
    }

    @Override
    public int getMaxTextLineWidth() {
        return 60;
    }
}
