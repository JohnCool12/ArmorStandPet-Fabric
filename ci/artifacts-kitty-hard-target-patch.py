from pathlib import Path
import json

src = Path('common/src/main/java/artifacts/mixin/ability/kittyslippers')
src.mkdir(parents=True, exist_ok=True)
(src / 'MobTargetMixin.java').write_text(r'''package artifacts.mixin.ability.kittyslippers;

import artifacts.equipment.EquipmentHelper;
import artifacts.registry.ModDataComponents;
import artifacts.registry.ModTags;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.monster.Phantom;
import net.minecraft.world.entity.player.Player;
import org.jetbrains.annotations.Nullable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.ModifyVariable;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Mob.class)
public abstract class MobTargetMixin {

    @Unique
    private static boolean artifacts$kittySlippersBlockTarget(Mob mob, @Nullable LivingEntity target) {
        if (!(target instanceof Player)) {
            return false;
        }

        if (ModTags.isInTag(mob.getType(), ModTags.CREEPERS)) {
            return EquipmentHelper.hasAbilityActive(ModDataComponents.CREEPER_REPELLENT.get(), target, true);
        }

        if (mob instanceof Phantom) {
            return EquipmentHelper.hasAbilityActive(ModDataComponents.PHANTOM_REPELLENT.get(), target, true);
        }

        return false;
    }

    @ModifyVariable(method = "setTarget", at = @At("HEAD"), argsOnly = true)
    private LivingEntity artifacts$rejectKittySlippersTarget(@Nullable LivingEntity target) {
        Mob mob = (Mob) (Object) this;
        return artifacts$kittySlippersBlockTarget(mob, target) ? null : target;
    }

    @Inject(method = "tick", at = @At("HEAD"))
    private void artifacts$clearRetainedKittySlippersTarget(CallbackInfo ci) {
        Mob mob = (Mob) (Object) this;
        if (mob.level().isClientSide()) {
            return;
        }

        LivingEntity target = mob.getTarget();
        if (artifacts$kittySlippersBlockTarget(mob, target)) {
            mob.setTarget(null);
        }
    }
}
''', encoding='utf-8')

p = Path('common/src/main/resources/mixins.artifacts.common.json')
data = json.loads(p.read_text(encoding='utf-8'))
name = 'ability.kittyslippers.MobTargetMixin'
if name not in data['mixins']:
    data['mixins'].append(name)
p.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
