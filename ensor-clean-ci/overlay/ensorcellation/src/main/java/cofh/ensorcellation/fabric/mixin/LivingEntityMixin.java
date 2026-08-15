package cofh.ensorcellation.fabric.mixin;

import cofh.ensorcellation.fabric.enchantment.EnsorEnchantments;
import cofh.ensorcellation.fabric.runtime.CombatRuntime;
import cofh.ensorcellation.fabric.runtime.EquipmentRuntime;
import cofh.ensorcellation.fabric.runtime.FoodRuntime;
import cofh.ensorcellation.fabric.runtime.RebukeRuntime;
import cofh.ensorcellation.fabric.runtime.ShieldRuntime;
import cofh.ensorcellation.fabric.runtime.SoulboundRuntime;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.BowItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.ModifyArg;
import org.spongepowered.asm.mixin.injection.ModifyVariable;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(LivingEntity.class)
abstract class LivingEntityMixin {
    @Shadow private int useItemRemaining;

    /** LivingHurtEvent-equivalent: after armor, before magic/enchantment mitigation. */
    @ModifyVariable(method = "actuallyHurt", at = @At(value = "STORE", ordinal = 0), ordinal = 0, argsOnly = false)
    private float ensor$hurtStage(float amount, DamageSource source) {
        return CombatRuntime.modifyHurt((LivingEntity) (Object) this, source, amount);
    }

    @Inject(method = "actuallyHurt", at = @At("TAIL"))
    private void ensor$postHurt(DamageSource source, float amount, CallbackInfo ci) {
        Entity attacker = source.getEntity();
        if (attacker != null) RebukeRuntime.onPostHurt((LivingEntity) (Object) this, attacker);
    }

    /** LivingDamageEvent-equivalent: immediately before the final health write. */
    @ModifyArg(method = "actuallyHurt", at = @At(value = "INVOKE", target = "Lnet/minecraft/world/entity/LivingEntity;setHealth(F)V"), index = 0)
    private float ensor$mercyHealth(float newHealth, DamageSource source, float incomingAmount) {
        LivingEntity self = (LivingEntity) (Object) this;
        return CombatRuntime.mercyHealth(self, source, newHealth);
    }

    @Inject(method = "die", at = @At("HEAD"))
    private void ensor$death(DamageSource source, CallbackInfo ci) {
        LivingEntity self = (LivingEntity) (Object) this;
        SoulboundRuntime.captureIfPlayer(self);
        CombatRuntime.recordKiller(self, source);
    }

    @Inject(method = "tick", at = @At("TAIL"))
    private void ensor$tick(CallbackInfo ci) {
        LivingEntity self = (LivingEntity) (Object) this;
        EquipmentRuntime.tick(self);
        ShieldRuntime.tick(self);
    }

    /** Original Quick Draw: subtract level * 10% * BowItem.MAX_DRAW_DURATION every use tick. */
    @Inject(method = "updatingUsingItem", at = @At("HEAD"))
    private void ensor$quickDraw(CallbackInfo ci) {
        LivingEntity self = (LivingEntity) (Object) this;
        ItemStack stack = self.getUseItem();
        if (!(stack.getItem() instanceof BowItem)) return;
        int level = EnsorEnchantments.level(stack, self.level(), "quick_draw");
        if (level > 0) {
            useItemRemaining -= (int) (level * 0.1F * BowItem.MAX_DRAW_DURATION);
        }
    }

    @Inject(method = "eat", at = @At("RETURN"))
    private void ensor$gourmand(Level level, ItemStack stack, net.minecraft.world.food.FoodProperties food, CallbackInfo ci) {
        FoodRuntime.afterEat((LivingEntity) (Object) this, food);
    }

    @Inject(method = "teleport", at = @At("HEAD"), cancellable = true)
    private void ensor$enderference(double x, double y, double z, boolean particles, CallbackInfoReturnable<Boolean> cir) {
        if (CombatRuntime.blocksTeleport((LivingEntity) (Object) this)) cir.setReturnValue(false);
    }
}
