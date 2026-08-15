package cofh.ensorcellation.fabric.mixin;

import cofh.ensorcellation.fabric.config.EnsorConfig;
import cofh.ensorcellation.fabric.enchantment.EnsorEnchantments;
import it.unimi.dsi.fastutil.objects.ObjectArrayList;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.projectile.FishingHook;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.LootTable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/** Original Angler semantics: each successful level is an independent fishing loot-table reroll. */
@Mixin(FishingHook.class)
abstract class FishingHookMixin {

    @Redirect(
            method = "retrieve",
            at = @At(
                    value = "INVOKE",
                    target = "Lnet/minecraft/world/level/storage/loot/LootTable;getRandomItems(Lnet/minecraft/world/level/storage/loot/LootParams;)Lit/unimi/dsi/fastutil/objects/ObjectArrayList;"
            )
    )
    private ObjectArrayList<ItemStack> ensor$anglerRerolls(LootTable table, LootParams params) {
        ObjectArrayList<ItemStack> result = table.getRandomItems(params);
        FishingHook hook = (FishingHook) (Object) this;
        if (!(hook.getPlayerOwner() instanceof ServerPlayer player)) return result;

        int level = EnsorEnchantments.level(player.getMainHandItem(), player.level(), "angler");
        if (level <= 0) return result;
        int chance = EnsorConfig.integer("angler.effect_chance", 50);
        for (int i = 0; i < level; i++) {
            if (player.getRandom().nextInt(100) < chance) {
                result.addAll(table.getRandomItems(params));
            }
        }
        return result;
    }
}
