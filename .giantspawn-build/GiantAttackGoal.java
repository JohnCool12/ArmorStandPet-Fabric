package com.natamus.giantspawn.ai;

import net.minecraft.world.entity.ai.goal.MeleeAttackGoal;
import net.minecraft.world.entity.monster.Giant;

/**
 * Giant-compatible equivalent of vanilla ZombieAttackGoal's aggression wrapper.
 *
 * ZombieAttackGoal itself requires a Zombie instance, so Giant cannot use it
 * directly. MeleeAttackGoal remains responsible for pathing, pursuit and the
 * actual attack cooldown; this class only mirrors the zombie arm/aggressive
 * state around that real cooldown.
 */
public class GiantAttackGoal extends MeleeAttackGoal {
    private final Giant giant;
    private int raiseArmTicks;

    public GiantAttackGoal(Giant giant, double speed, boolean pauseWhenMobIdle) {
        super(giant, speed, pauseWhenMobIdle);
        this.giant = giant;
    }

    @Override
    public void start() {
        super.start();
        this.raiseArmTicks = 0;
    }

    @Override
    public void stop() {
        super.stop();
        this.giant.setAggressive(false);
    }

    @Override
    public void tick() {
        super.tick();
        ++this.raiseArmTicks;

        // Match vanilla ZombieAttackGoal: consult MeleeAttackGoal's real
        // cooldown instead of maintaining a disconnected local attack timer.
        this.giant.setAggressive(
            this.raiseArmTicks >= 5
                && this.getTicksUntilNextAttack() < this.getAttackInterval() / 2
        );
    }
}
