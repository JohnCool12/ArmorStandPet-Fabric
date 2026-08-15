package cofh.ensorcellation.fabric.runtime;

import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.entity.event.v1.ServerPlayerEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.server.level.ServerLevel;

/** Fabric event wiring for the original Ensorcellation common events. */
public final class EnsorEvents {
    private static boolean registered;

    public static void register() {
        MiningRuntime.register();
        if (registered) return;
        registered = true;

        ServerLivingEntityEvents.AFTER_DEATH.register((dead, source) -> {
            CombatRuntime.onDeath(dead, source);
            if (dead.level() instanceof ServerLevel level) LootRuntime.onDeath(level, dead, source);
        });

        ServerLivingEntityEvents.AFTER_DAMAGE.register((defender, source, baseDamage, damageTaken, blocked) -> {
            if (blocked) ShieldRuntime.onBlocked(defender, source, baseDamage);
        });

        ServerEntityEvents.EQUIPMENT_CHANGE.register((living, slot, previous, current) -> EquipmentRuntime.refresh(living));
        ServerEntityEvents.ENTITY_LOAD.register((entity, world) -> {
            if (entity instanceof net.minecraft.world.entity.LivingEntity living) EquipmentRuntime.refresh(living);
        });

        ServerPlayerEvents.AFTER_RESPAWN.register((oldPlayer, newPlayer, alive) -> {
            if (!alive) SoulboundRuntime.restore(newPlayer);
        });

        ServerTickEvents.END_SERVER_TICK.register(server -> RebukeRuntime.flushPendingFire());
    }

    private EnsorEvents() {}
}
