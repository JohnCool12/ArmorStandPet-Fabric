package cofh.ensorcellation.fabric.runtime;

import cofh.ensorcellation.fabric.enchantment.EnsorEnchantments;
import net.fabricmc.fabric.api.entity.event.v1.ServerEntityCombatEvents;
import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.entity.event.v1.ServerPlayerEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.ExperienceOrb;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.item.ItemEntity;

public final class EnsorEvents {
    public static void register() {
        MiningRuntime.register();

        ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> {
            if (entity.level() instanceof ServerLevel serverLevel) LootRuntime.onDeath(serverLevel, entity, source);
        });
        ServerEntityCombatEvents.AFTER_KILLED_OTHER_ENTITY.register((world, entity, killedEntity) -> {
            if (entity instanceof LivingEntity attacker && killedEntity instanceof LivingEntity dead) CombatRuntime.afterKill(attacker, dead);
        });
        ServerTickEvents.END_SERVER_TICK.register(server -> RebukeRuntime.flushPendingFire());
        ServerPlayerEvents.COPY_FROM.register((oldPlayer, newPlayer, alive) -> SoulboundRuntime.copyOnRespawn(oldPlayer, newPlayer, alive));
        ServerPlayerEvents.AFTER_RESPAWN.register((oldPlayer, newPlayer, alive) -> SoulboundRuntime.restore(newPlayer));
    }

    /** World entity-add XP hook used by block/mob/fishing paths. */
    public static void onXpOrb(ExperienceOrb orb) {
        XpRuntime.onOrbSpawn(orb);
    }

    public static void onItemEntity(ItemEntity item) {
        // reserved for fishing/loot paths wired in the next parity stage
    }

    private EnsorEvents() {}
}
