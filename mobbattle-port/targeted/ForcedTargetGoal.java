package io.github.flemmli97.mobbattle.common.entity.goal;

import io.github.flemmli97.mobbattle.common.utils.Utils;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.target.TargetGoal;

import java.util.EnumSet;

/**
 * Owns the target-selection channel while Mob Battle has an explicit forced
 * opponent, without taking over movement or attack execution.
 *
 * The previous Fabric parity port intentionally used no Goal flags here. That
 * allowed vanilla target goals to run simultaneously. Iron Golem's native
 * target goals can reject non-hostile entities such as Guard Villagers and then
 * clear Mob#setTarget after this goal sets it, so the subsequent melee goal sees
 * no target. Using TARGET is the correct narrow ownership boundary: native
 * movement, look, melee/ranged attacks, animations, cooldowns and navigation are
 * untouched; only competing target selectors are suspended for the duration of
 * the forced Mob Battle assignment.
 */
public class ForcedTargetGoal extends TargetGoal {
    public ForcedTargetGoal(Mob mob) {
        super(mob, false, false);
        this.setFlags(EnumSet.of(Goal.Flag.TARGET));
    }

    private LivingEntity resolveTarget() {
        return Utils.findForcedTarget(this.mob);
    }

    @Override
    public boolean canUse() {
        this.targetMob = this.resolveTarget();
        return this.targetMob != null;
    }

    @Override
    public boolean canContinueToUse() {
        this.targetMob = this.resolveTarget();
        return this.targetMob != null;
    }

    @Override
    public void start() {
        LivingEntity target = this.resolveTarget();
        if (target != null) {
            this.targetMob = target;
            Utils.refreshAttackTarget(this.mob, target);
        }
        super.start();
    }

    @Override
    public void tick() {
        LivingEntity target = this.resolveTarget();
        if (target != null) {
            this.targetMob = target;
            Utils.refreshAttackTarget(this.mob, target);
        }
    }

    @Override
    public void stop() {
        LivingEntity current = this.mob.getTarget();
        if (current != null && Utils.isForcedOpponent(this.mob, current)) {
            this.mob.setTarget(null);
        }
        this.targetMob = null;
        super.stop();
    }

    @Override
    public boolean requiresUpdateEveryTick() {
        return true;
    }

    @Override
    public boolean isInterruptable() {
        return true;
    }
}
