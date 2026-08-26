from pathlib import Path
import json

root = Path('project')
mixin_dir = root / 'src/main/java/com/mcmoddev/golems/mixin'
mixin_dir.mkdir(parents=True, exist_ok=True)

melee = r'''package com.mcmoddev.golems.mixin;

import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.goal.MeleeAttackGoal;
import net.minecraft.world.entity.ai.navigation.PathNavigation;
import net.minecraft.world.entity.animal.IronGolem;
import net.minecraft.world.level.pathfinder.Path;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Constant;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.ModifyConstant;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(MeleeAttackGoal.class)
public abstract class IronGolemMeleeAttackGoalMixin {

    @Shadow @Final protected PathfinderMob mob;

    @ModifyConstant(
            method = "canUse",
            constant = @Constant(longValue = 20L),
            require = 1
    )
    private long extraGolems$shortenIronGolemMeleeRestartDelay(long original) {
        return this.mob instanceof IronGolem ? 2L : original;
    }

    @Redirect(
            method = "tick",
            at = @At(
                    value = "INVOKE",
                    target = "Lnet/minecraft/world/entity/ai/navigation/PathNavigation;moveTo(Lnet/minecraft/world/entity/Entity;D)Z"
            ),
            require = 1
    )
    private boolean extraGolems$preserveIronGolemPathOnFailedRefresh(
            PathNavigation navigation, Entity target, double speed) {
        if (!(this.mob instanceof IronGolem)) {
            return navigation.moveTo(target, speed);
        }

        final Path previous = navigation.getPath();
        final Path refreshed = navigation.createPath(target, 1);
        if (refreshed != null) {
            return navigation.moveTo(refreshed, speed);
        }

        if (previous != null && !previous.isDone()) {
            navigation.setSpeedModifier(speed);
            return true;
        }

        if (target instanceof LivingEntity living
                && living.isAlive()
                && !this.mob.isInWaterOrBubble()
                && this.mob.getSensing().hasLineOfSight(living)
                && this.mob.distanceToSqr(living) <= 64.0D
                && Math.abs(living.getY() - this.mob.getY()) <= 1.5D) {
            this.mob.getMoveControl().setWantedPosition(
                    living.getX(), living.getY(), living.getZ(), speed);
            return true;
        }

        return false;
    }

    @Inject(method = "tick", at = @At("TAIL"))
    private void extraGolems$bridgeShortIronGolemPursuitGap(CallbackInfo ci) {
        if (!(this.mob instanceof IronGolem) || this.mob.isInWaterOrBubble()) {
            return;
        }

        final LivingEntity target = this.mob.getTarget();
        if (target == null || !target.isAlive()) {
            return;
        }

        final PathNavigation navigation = this.mob.getNavigation();
        final double distance = this.mob.distanceToSqr(target);
        if (navigation.isDone()
                && distance > 4.0D
                && distance <= 64.0D
                && Math.abs(target.getY() - this.mob.getY()) <= 1.5D
                && this.mob.getSensing().hasLineOfSight(target)) {
            this.mob.getMoveControl().setWantedPosition(
                    target.getX(), target.getY(), target.getZ(), 1.0D);
        }
    }
}
'''

navigation = r'''package com.mcmoddev.golems.mixin;

import javax.annotation.Nullable;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.navigation.PathNavigation;
import net.minecraft.world.entity.animal.IronGolem;
import net.minecraft.world.level.pathfinder.Path;
import net.minecraft.world.phys.Vec3;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(PathNavigation.class)
public abstract class IronGolemPathNavigationMixin {

    @Shadow @Final protected Mob mob;
    @Shadow @Nullable protected Path path;

    @Inject(method = "followThePath", at = @At("HEAD"))
    private void extraGolems$advanceSatisfiedIronGolemDownStep(CallbackInfo ci) {
        if (!(this.mob instanceof IronGolem golem) || this.mob.isInWaterOrBubble()) {
            return;
        }

        final LivingEntity target = golem.getTarget();
        final Path current = this.path;
        if (target == null || !target.isAlive() || current == null || current.isDone()) {
            return;
        }

        final BlockPos node = current.getNextNodePos();
        final double verticalDrop = this.mob.getY() - node.getY();
        if (verticalDrop < 0.60D || verticalDrop > 1.35D) {
            return;
        }

        final double dx = this.mob.getX() - (node.getX() + 0.5D);
        final double dz = this.mob.getZ() - (node.getZ() + 0.5D);
        final double reach = Math.max(0.72D, Math.min(1.0D, this.mob.getBbWidth() * 0.56D));
        if (dx * dx + dz * dz > reach * reach) {
            return;
        }

        final int index = current.getNextNodeIndex();
        if (index + 1 >= current.getNodeCount()) {
            return;
        }

        final Vec3 following = current.getEntityPosAtNode(this.mob, index + 1);
        if (following.y > node.getY() + 0.60D) {
            return;
        }

        current.advance();
    }
}
'''

move = r'''package com.mcmoddev.golems.mixin;

import net.minecraft.util.Mth;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.control.MoveControl;
import net.minecraft.world.entity.animal.IronGolem;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(MoveControl.class)
public abstract class IronGolemMoveControlMixin {

    @Shadow @Final protected Mob mob;
    @Shadow protected double wantedX;
    @Shadow protected double wantedY;
    @Shadow protected double wantedZ;

    @Unique private float extraGolems$preMoveYaw;
    @Unique private double extraGolems$wantedXSnapshot;
    @Unique private double extraGolems$wantedYSnapshot;
    @Unique private double extraGolems$wantedZSnapshot;

    @Inject(method = "tick", at = @At("HEAD"))
    private void extraGolems$captureIronGolemMoveState(CallbackInfo ci) {
        this.extraGolems$preMoveYaw = this.mob.getYRot();
        this.extraGolems$wantedXSnapshot = this.wantedX;
        this.extraGolems$wantedYSnapshot = this.wantedY;
        this.extraGolems$wantedZSnapshot = this.wantedZ;
    }

    @Inject(method = "tick", at = @At("TAIL"))
    private void extraGolems$preventIronGolemDownStepSpin(CallbackInfo ci) {
        if (!(this.mob instanceof IronGolem golem) || this.mob.isInWaterOrBubble()) {
            return;
        }

        final LivingEntity target = golem.getTarget();
        if (target == null || !target.isAlive()) {
            return;
        }

        final double drop = this.mob.getY() - this.extraGolems$wantedYSnapshot;
        final double nodeDx = this.extraGolems$wantedXSnapshot - this.mob.getX();
        final double nodeDz = this.extraGolems$wantedZSnapshot - this.mob.getZ();
        if (drop < 0.40D || drop > 1.40D || nodeDx * nodeDx + nodeDz * nodeDz > 2.25D) {
            return;
        }

        final float afterYaw = this.mob.getYRot();
        final float nodeTurn = Math.abs(Mth.wrapDegrees(afterYaw - this.extraGolems$preMoveYaw));
        if (nodeTurn < 50.0F) {
            return;
        }

        final double targetDx = target.getX() - this.mob.getX();
        final double targetDz = target.getZ() - this.mob.getZ();
        if (targetDx * targetDx + targetDz * targetDz < 0.25D) {
            return;
        }

        final float targetYaw = (float)(Mth.atan2(targetDz, targetDx) * (180.0D / Math.PI)) - 90.0F;
        final float targetTurn = Mth.wrapDegrees(targetYaw - this.extraGolems$preMoveYaw);
        if (Math.abs(targetTurn) + 15.0F >= nodeTurn) {
            return;
        }

        final float correctedTurn = Mth.clamp(targetTurn, -30.0F, 30.0F);
        this.mob.setYRot(this.extraGolems$preMoveYaw + correctedTurn);
    }
}
'''

(mixin_dir / 'IronGolemMeleeAttackGoalMixin.java').write_text(melee)
(mixin_dir / 'IronGolemPathNavigationMixin.java').write_text(navigation)
(mixin_dir / 'IronGolemMoveControlMixin.java').write_text(move)

cfg = root / 'src/main/resources/golems.mixins.json'
data = json.loads(cfg.read_text())
mixins = data.setdefault('mixins', [])
for name in (
    'IronGolemMeleeAttackGoalMixin',
    'IronGolemPathNavigationMixin',
    'IronGolemMoveControlMixin',
):
    if name not in mixins:
        mixins.append(name)
cfg.write_text(json.dumps(data, indent=2) + '\n')

print('Installed shared vanilla + Extra Iron Golem smooth combat movement mixins.')
