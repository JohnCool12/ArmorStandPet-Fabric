package com.kyanite.deeperdarker.content.blocks.entity;

import com.kyanite.deeperdarker.content.DDBlockEntities;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.SignBlockEntity;
import net.minecraft.world.level.block.state.BlockState;

/** Sign entity whose superclass is initialized with the mod's own type. */
public class DDSignBlockEntity extends SignBlockEntity {
    public DDSignBlockEntity(BlockPos pos, BlockState blockState) {
        super(DDBlockEntities.DEEPER_DARKER_SIGNS.get(), pos, blockState);
    }
}
