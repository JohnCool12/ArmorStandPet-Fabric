package io.github.flemmli97.mobbattle.mixin;

import io.github.flemmli97.mobbattle.common.utils.Utils;
import net.minecraft.world.entity.Entity;
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
 * The important rule here is that Mob Battle may bypass GuardEntity's target-type
 * refusal for the explicitly forced opponent, but it must NOT suppress the guard's
 * own temporary target clears. Those clears are used by native combat/action goals
 * to transition cleanly between shield/item/ranged/melee states. Blocking them made
 * a Mob Battle guard keep a combat target through unrelated actions and could make
 * melee damage look like contact damage with no natural attack presentation.
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

    /**
     * GuardEntity refuses guards/villagers/iron golems in its own setTarget override.
     * Bypass only that refusal for the explicit Mob Battle opponent. Native null clears
     * and all unrelated target changes are left completely alone.
     */
    @Inject(method = "method_5980", at = @At("HEAD"), cancellable = true, require = 0, remap = false)
    private void mobbattle$setRealGuardTarget(@Nullable LivingEntity proposedTarget, CallbackInfo ci) {
        Mob self = (Mob) (Object) this;
        if (proposedTarget != null && Utils.isBattleOpponent(self, proposedTarget)) {
            // Do not start/restart combat while Guard Villagers is actively using an
            // item (shield, food, bow/crossbow transition, etc.). If its native AI
            // temporarily cleared the target for that action, ForcedTargetGoal can
            // retry once the action finishes.
            if (this.isUsingItem() && self.getTarget() != proposedTarget) {
                ci.cancel();
                return;
            }
            super.setTarget(proposedTarget);
            ci.cancel();
        }
    }

    /**
     * Extra safety for the exact symptom reported in-game: while a guard is visibly
     * using another item/action, do not let a forced Mob Battle opponent receive a
     * hidden melee hit merely because its hitbox touches the guard. Normal native
     * melee/kick attacks remain unchanged when the guard is not using an item.
     */
    @Inject(method = "method_6121", at = @At("HEAD"), cancellable = true, require = 0, remap = false)
    private void mobbattle$noHiddenMeleeWhileUsingItem(Entity target, CallbackInfoReturnable<Boolean> cir) {
        Mob self = (Mob) (Object) this;
        if (target instanceof LivingEntity living
                && Utils.isBattleOpponent(self, living)
                && this.isUsingItem()) {
            cir.setReturnValue(false);
        }
    }
}
