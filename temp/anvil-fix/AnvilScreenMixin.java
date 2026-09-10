package limitless.enchantments.mixin;

import net.minecraft.client.gui.screens.inventory.AnvilScreen;
import net.minecraft.world.entity.player.Abilities;
import org.objectweb.asm.Opcodes;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/**
 * Makes the anvil GUI follow the server-authoritative synchronized output slot
 * rather than an unsynchronized client-local Limitless threshold field.
 */
@Mixin(AnvilScreen.class)
public class AnvilScreenMixin {
    @Redirect(
            method = "renderLabels",
            at = @At(
                    value = "FIELD",
                    target = "Lnet/minecraft/world/entity/player/Abilities;instabuild:Z",
                    opcode = Opcodes.GETFIELD,
                    ordinal = 0
            ),
            require = 1
    )
    private boolean limitless$followServerAnvilAvailability(Abilities abilities) {
        AnvilScreen screen = (AnvilScreen) (Object) this;
        return abilities.instabuild || screen.getMenu().getSlot(2).hasItem();
    }
}
