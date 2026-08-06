package com.kyanite.deeperdarker.mixin;

import com.kyanite.deeperdarker.content.items.SculkTransmitterItem;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractFurnaceMenu;
import net.minecraft.world.inventory.BeaconMenu;
import net.minecraft.world.inventory.BrewingStandMenu;
import net.minecraft.world.inventory.CartographyTableMenu;
import net.minecraft.world.inventory.ChestMenu;
import net.minecraft.world.inventory.CraftingMenu;
import net.minecraft.world.inventory.DispenserMenu;
import net.minecraft.world.inventory.EnchantmentMenu;
import net.minecraft.world.inventory.GrindstoneMenu;
import net.minecraft.world.inventory.HopperMenu;
import net.minecraft.world.inventory.ItemCombinerMenu;
import net.minecraft.world.inventory.LoomMenu;
import net.minecraft.world.inventory.ShulkerBoxMenu;
import net.minecraft.world.inventory.StonecutterMenu;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@SuppressWarnings("unused")
@Mixin({
        AbstractFurnaceMenu.class,
        BeaconMenu.class,
        BrewingStandMenu.class,
        CartographyTableMenu.class,
        ChestMenu.class,
        CraftingMenu.class,
        DispenserMenu.class,
        EnchantmentMenu.class,
        GrindstoneMenu.class,
        HopperMenu.class,
        ItemCombinerMenu.class,
        LoomMenu.class,
        ShulkerBoxMenu.class,
        StonecutterMenu.class
})
public class ContainerMenuMixin {
    @Inject(method = "stillValid", at = @At("HEAD"), cancellable = true)
    private void deeperdarker$allowRemoteContainer(Player player, CallbackInfoReturnable<Boolean> cir) {
        if (SculkTransmitterItem.stillValid(player)) {
            cir.setReturnValue(true);
        }
    }
}
