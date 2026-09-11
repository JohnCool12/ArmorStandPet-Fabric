package io.github.flemmli97.mobbattle.mixin;

import io.github.flemmli97.mobbattle.common.utils.Utils;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Pseudo
@Mixin(targets = "org.betterx.betternether.entity.EntitySkull", remap = false)
public abstract class BetterNetherSkullCompatMixin {
    @Unique
    private int mobbattle$forcedAttackCooldown;

    @Inject(method = "method_5773", at = @At("TAIL"), remap = false, require = 0)
    private void mobbattle$driveForcedSkullCombat(CallbackInfo ci) {
        Mob self = (Mob) (Object) this;
        LivingEntity target = Utils.findForcedTarget(self);
        if (target == null)
            return;

        Utils.refreshAttackTarget(self, target);

        Vec3 delta = target.position().add(0.0, target.getBbHeight() * 0.5, 0.0).subtract(self.position());
        if (delta.lengthSqr() > 1.0E-6) {
            double speed = self.getAttributeValue(Attributes.MOVEMENT_SPEED);
            if (!Double.isFinite(speed) || speed <= 0.0)
                speed = 0.5;
            speed = Math.max(0.1, Math.min(speed, 0.5));
            self.setDeltaMovement(delta.normalize().scale(speed));
            self.getLookControl().setLookAt(target, 360.0F, 360.0F);
        }

        if (this.mobbattle$forcedAttackCooldown > 0)
            --this.mobbattle$forcedAttackCooldown;

        double reach = (self.getBbWidth() + target.getBbWidth()) * 0.5 + 0.35;
        if (this.mobbattle$forcedAttackCooldown <= 0 && self.distanceToSqr(target) <= reach * reach) {
            if (self.doHurtTarget(target))
                this.mobbattle$forcedAttackCooldown = 25;
        }
    }

    @Inject(method = "method_5694", at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private void mobbattle$ignoreUnforcedPlayerCollision(Player player, CallbackInfo ci) {
        Mob self = (Mob) (Object) this;
        LivingEntity forced = Utils.findForcedTarget(self);
        if (forced != null && !Utils.isForcedOpponent(self, player))
            ci.cancel();
    }
}
