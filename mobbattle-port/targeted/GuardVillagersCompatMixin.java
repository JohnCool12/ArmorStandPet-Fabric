package io.github.flemmli97.mobbattle.mixin;

import io.github.flemmli97.mobbattle.common.utils.Utils;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.level.Level;
import org.jetbrains.annotations.Nullable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Targeted compatibility for Guard Villagers 2.1.2 on Minecraft 1.21.1.
 *
 * GuardEntity overrides both LivingEntity#canTarget(LivingEntity) and
 * Mob#setTarget(LivingEntity). In particular, its setTarget override refuses
 * guards, villagers and iron golems before vanilla Mob#setTarget is reached.
 * That can leave Mob Battle's ForcedTargetGoal owning a UUID while the guard's
 * real target remains null: a "ghost" target which blocks normal target changes
 * but never starts the guard's native melee/bow/crossbow goals.
 *
 * For an opponent that Mob Battle actually owns, bypass only those GuardEntity
 * restrictions and delegate straight to the vanilla Mob/PathfinderMob target
 * setter. The guard's own combat goals, navigation, weapon handling, shield,
 * animations and attack timing remain responsible for the fight.
 */
@Pseudo
@Mixin(targets = "dev.sterner.guardvillagers.common.entity.GuardEntity", remap = false)
public abstract class GuardVillagersCompatMixin extends PathfinderMob {

    protected GuardVillagersCompatMixin(EntityType<? extends PathfinderMob> type, Level level) {
        super(type, level);
    }

    /** GuardEntity intermediary override of LivingEntity#canTarget(LivingEntity). */
    @Inject(method = "method_18395", at = @At("HEAD"), cancellable = true, require = 0, remap = false)
    private void mobbattle$allowRealCombatAgainstBattleOpponent(LivingEntity target,
                                                                 CallbackInfoReturnable<Boolean> cir) {
        Mob self = (Mob) (Object) this;
        if (target != null && Utils.isBattleOpponent(self, target)) {
            cir.setReturnValue(true);
        }
    }

    /** GuardEntity intermediary override of Mob#setTarget(LivingEntity). */
    @Inject(method = "method_5980", at = @At("HEAD"), cancellable = true, require = 0, remap = false)
    private void mobbattle$setRealGuardTarget(@Nullable LivingEntity proposedTarget, CallbackInfo ci) {
        Mob self = (Mob) (Object) this;
        LivingEntity forced = Utils.findForcedTarget(self);

        if (proposedTarget != null && Utils.isBattleOpponent(self, proposedTarget)) {
            super.setTarget(proposedTarget);
            ci.cancel();
            return;
        }

        if (forced != null) {
            ci.cancel();
        }
    }
}
