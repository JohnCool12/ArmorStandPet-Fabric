from pathlib import Path
import json

root = Path('project')
mixin_dir = root / 'src/main/java/com/mcmoddev/golems/mixin'
mixin_dir.mkdir(parents=True, exist_ok=True)

java = r'''package com.mcmoddev.golems.mixin;

import net.minecraft.world.Difficulty;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.animal.IronGolem;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/**
 * Extends Minecraft's normal player-facing mob-damage difficulty scaling to
 * Iron-Golem melee hits against non-player living entities.
 *
 * GolemBase delegates its melee hit to IronGolem#doHurtTarget, so this single
 * hook applies equally to vanilla Iron Golems and Extra Golems. Player victims
 * are deliberately untouched so vanilla's normal damage-type scaling applies
 * exactly once.
 */
@Mixin(IronGolem.class)
public abstract class IronGolemDamageDifficultyMixin {

    @Redirect(
            method = "doHurtTarget",
            at = @At(
                    value = "INVOKE",
                    target = "Lnet/minecraft/world/entity/Entity;hurt(Lnet/minecraft/world/damagesource/DamageSource;F)Z"
            )
    )
    private boolean extraGolems$scaleNonPlayerMeleeDamageByDifficulty(
            Entity target, DamageSource source, float amount) {
        if (target instanceof LivingEntity && !(target instanceof Player)) {
            Difficulty difficulty = ((IronGolem) (Object) this).level().getDifficulty();
            amount = switch (difficulty) {
                case PEACEFUL -> 0.0F;
                case EASY -> Math.min(amount * 0.5F + 1.0F, amount);
                case NORMAL -> amount;
                case HARD -> amount * 1.5F;
            };
        }
        return target.hurt(source, amount);
    }
}
'''
(mixin_dir / 'IronGolemDamageDifficultyMixin.java').write_text(java)

cfg = root / 'src/main/resources/golems.mixins.json'
data = json.loads(cfg.read_text())
mixins = data.setdefault('mixins', [])
name = 'IronGolemDamageDifficultyMixin'
if name not in mixins:
    mixins.append(name)
cfg.write_text(json.dumps(data, indent=2) + '\n')

print('Installed IronGolemDamageDifficultyMixin for vanilla + Extra Golem non-player melee scaling.')
