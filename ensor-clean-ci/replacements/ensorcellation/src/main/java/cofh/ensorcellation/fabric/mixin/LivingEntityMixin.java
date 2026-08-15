package cofh.ensorcellation.fabric.mixin;

import cofh.ensorcellation.fabric.enchantment.EnsorEnchantments;
import cofh.ensorcellation.fabric.runtime.CombatRuntime;
import cofh.ensorcellation.fabric.runtime.PilferRuntime;
import cofh.ensorcellation.fabric.runtime.RebukeRuntime;
import cofh.ensorcellation.fabric.runtime.ShieldRuntime;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.BowItem;
import net.minecraft.world.item.ItemStack;
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

    @Inject(method = "hurt", at = @At("HEAD"), cancellable = true)
    private void ensor$magicEdge(DamageSource source, float amount, CallbackInfoReturnable<Boolean> cir) {
        LivingEntity self = (LivingEntity) (Object) this;
        if (self.level() instanceof ServerLevel level && CombatRuntime.shouldRewriteMagicEdge(self, source)) {
            cir.setReturnValue(CombatRuntime.hurtAsMagic(self, level, source, amount));
        }
    }

    @ModifyVariable(method = "actuallyHurt", at = @At("HEAD"), argsOnly = true, ordinal = 0)
    private float ensor$modifyHurtAmount(float amount, DamageSource source) {
        return CombatRuntime.modifyHurtAmount((LivingEntity) (Object) this, source, amount);
    }

    @ModifyArg(method = "actuallyHurt", at = @At(value = "INVOKE", target = "Lnet/minecraft/world/entity/LivingEntity;setHealth(F)V"), index = 0)
    private float ensor$mercy(float proposedHealth, DamageSource source, float amount) {
        return CombatRuntime.mercyHealth((LivingEntity) (Object) this, source, proposedHealth);
    }

    @Inject(method = "actuallyHurt", at = @At("RETURN"))
    private void ensor$postHurt(DamageSource source, float amount, CallbackInfo ci) {
        LivingEntity self = (LivingEntity) (Object) this;
        CombatRuntime.afterSuccessfulDamage(self, source);
        if (source.getEntity() instanceof LivingEntity attacker) PilferRuntime.tryPilfer(attacker, self);
        Entity attacker = source.getEntity();
        if (attacker != null) RebukeRuntime.onPostHurt(self, attacker);
    }

    /**
     * CoFH Core ArcheryEvents parity: during the normal 20-tick bow draw window,
     * each Quick Draw level removes one additional remaining-use tick per game tick.
     * Hooking LivingEntity.tick avoids relying on a private helper method name.
     */
    @Inject(method = "tick", at = @At("HEAD"))
    private void ensor$quickDrawTick(CallbackInfo ci) {
        LivingEntity self = (LivingEntity) (Object) this;
        if (!self.isUsingItem()) return;
        ItemStack stack = self.getUseItem();
        if (!(stack.getItem() instanceof BowItem)) return;
        int level = EnsorEnchantments.level(stack, self.level(), "quick_draw");
        if (level > 0 && useItemRemaining > stack.getUseDuration(self) - BowItem.MAX_DRAW_DURATION) {
            useItemRemaining -= level;
        }
    }

    @Inject(method = "tick", at = @At("TAIL"))
    private void ensor$shieldTick(CallbackInfo ci) {
        ShieldRuntime.tick((LivingEntity) (Object) this);
    }
}
