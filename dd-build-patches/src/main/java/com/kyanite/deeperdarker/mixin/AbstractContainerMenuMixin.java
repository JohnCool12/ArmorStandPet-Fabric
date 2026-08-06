package com.kyanite.deeperdarker.mixin;

import com.kyanite.deeperdarker.content.DDDataAttachments;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(AbstractContainerMenu.class)
public abstract class AbstractContainerMenuMixin {
    @Inject(method = "removed", at = @At("HEAD"))
    private void deeperdarker$clearRemoteContainerState(Player player, CallbackInfo ci) {
        DDDataAttachments.get(player).usingTransmitter = false;
    }
}
