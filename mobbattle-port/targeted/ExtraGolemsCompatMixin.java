package io.github.flemmli97.mobbattle.mixin;

import io.github.flemmli97.mobbattle.common.utils.Utils;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.animal.IronGolem;
import net.minecraft.world.level.Level;
import org.jetbrains.annotations.Nullable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Targeted compatibility for the user's Extra Golems Reborn Fabric 1.21.1
 * V4/26.1.2-backport lineage.
 *
 * GolemBase can rebuild its goal and target selectors when material/behavior
 * state is refreshed. Mob Battle's forced UUID ownership survives that rebuild,
 * but its injected target selector goal can be removed and the real Mob target
 * can consequently become null. This produces the appearance that the Mob
 * Battle item did nothing.
 *
 * This adapter does NOT implement combat. It only makes sure that the explicit
 * Mob Battle opponent reaches/stays in the real IronGolem target field after
 * GolemBase's own AI tick. Native Extra Golems / IronGolem goals and
 * BackportRuntime remain responsible for navigation, attacks, ranged behavior,
 * cooldowns, fuel/inert states, animations, and damage.
 */
@Pseudo
@Mixin(targets = "com.mcmoddev.golems.entity.GolemBase", remap = false)
public abstract class ExtraGolemsCompatMixin extends IronGolem {

    protected ExtraGolemsCompatMixin(EntityType<? extends IronGolem> type, Level level) {
        super(type, level);
    }

    /**
     * Let GolemBase and its BackportRuntime hooks process the target first. If
     * that custom setter failed to retain an explicit Mob Battle opponent,
     * write only the vanilla IronGolem target field as a narrow fallback.
     */
    @Inject(method = "method_5980", at = @At("RETURN"), require = 0, remap = false)
    private void mobbattle$ensureForcedTargetAccepted(@Nullable LivingEntity proposedTarget, CallbackInfo ci) {
        Mob self = (Mob) (Object) this;
        if (proposedTarget != null
                && Utils.isBattleOpponent(self, proposedTarget)
                && self.getTarget() != proposedTarget) {
            super.setTarget(proposedTarget);
        }
    }

    /**
     * Reconcile after GolemBase's own tick because its selector/behavior refresh
     * can erase Mob Battle's goal or target later than ordinary target setup.
     * This deliberately does not invoke attacks or navigation itself.
     */
    @Inject(method = "method_5773", at = @At("TAIL"), require = 0, remap = false)
    private void mobbattle$restoreForcedTargetAfterGolemAi(CallbackInfo ci) {
        Mob self = (Mob) (Object) this;
        if (self.level().isClientSide() || self.isNoAi()) {
            return;
        }

        LivingEntity forced = Utils.findForcedTarget(self);
        if (forced != null && self.getTarget() != forced) {
            self.setTarget(forced);
            if (self.getTarget() != forced) {
                super.setTarget(forced);
            }
        }
    }
}
