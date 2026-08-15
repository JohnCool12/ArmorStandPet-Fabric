package cofh.ensorcellation.fabric.mixin;

import cofh.ensorcellation.fabric.runtime.FoodRuntime;
import cofh.ensorcellation.fabric.runtime.MiningRuntime;
import cofh.ensorcellation.fabric.runtime.SoulboundRuntime;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.food.FoodProperties;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(Player.class)
abstract class PlayerMixin {
    @Inject(method = "eat", at = @At("RETURN"))
    private void ensor$gourmand(Level level, ItemStack stack, FoodProperties food, CallbackInfo ci) {
        FoodRuntime.afterEat((Player) (Object) this, food);
    }

    @Inject(method = "dropEquipment", at = @At("HEAD"))
    private void ensor$captureSoulbound(CallbackInfo ci) {
        if ((Object) this instanceof ServerPlayer player) SoulboundRuntime.capture(player);
    }

    @Inject(method = "getDestroySpeed", at = @At("RETURN"), cancellable = true)
    private void ensor$modifyDestroySpeed(BlockState state, CallbackInfoReturnable<Float> cir) {
        cir.setReturnValue(MiningRuntime.modifyDestroySpeed(cir.getReturnValueF(), (Player) (Object) this, state));
    }
}
