from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


mixin_path = Path("common/src/main/java/artifacts/mixin/compat/hardcorerevival/KnockoutHandlerMixin.java")
mixin_path.parent.mkdir(parents=True, exist_ok=True)
mixin_path.write_text(
    '''package artifacts.mixin.compat.hardcorerevival;

import artifacts.component.ability.DeathProtectionTeleport;
import artifacts.equipment.EquipmentHelper;
import artifacts.registry.ModDataComponents;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Pseudo
@Mixin(targets = "net.blay09.mods.hardcorerevival.handler.KnockoutHandler", remap = false)
public abstract class KnockoutHandlerMixin {

    @Inject(method = "isKnockoutEnabledFor", at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private static void artifacts$allowEquippedChorusTotem(
            ServerPlayer player,
            DamageSource damageSource,
            CallbackInfoReturnable<Boolean> cir
    ) {
        ItemStack equippedTotem = EquipmentHelper.reduceAbilities(
                ModDataComponents.DEATH_PROTECTION_TELEPORT.get(),
                player,
                true,
                true,
                ItemStack.EMPTY,
                (ability, stack, result) -> result.isEmpty() ? stack : result
        );

        if (!equippedTotem.isEmpty()) {
            cir.setReturnValue(false);
        }
    }
}
''',
    encoding="utf-8",
)

replace_once(
    "common/src/main/resources/mixins.artifacts.common.json",
    '    "compat.apoli.condition.type.entity.ExposedToSunEntityConditionTypeMixin",\n',
    '    "compat.apoli.condition.type.entity.ExposedToSunEntityConditionTypeMixin",\n'
    '    "compat.hardcorerevival.KnockoutHandlerMixin",\n',
)
