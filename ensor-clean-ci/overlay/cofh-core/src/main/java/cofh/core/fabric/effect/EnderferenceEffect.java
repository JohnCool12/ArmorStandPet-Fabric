package cofh.core.fabric.effect;

import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectCategory;

/**
 * Fabric 1.21.1 counterpart of CoFH Core's neutral Enderference effect.
 * The original effect is intentionally behaviorless; its behavior is supplied
 * by teleport/ender-pearl hooks.
 */
public final class EnderferenceEffect extends MobEffect {

    public EnderferenceEffect() {
        super(MobEffectCategory.NEUTRAL, 0x093755);
    }
}
