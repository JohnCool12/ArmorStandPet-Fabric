package cofh.ensorcellation.fabric.runtime;

import cofh.core.fabric.CoreContent;
import cofh.ensorcellation.fabric.config.EnsorConfig;
import cofh.ensorcellation.fabric.enchantment.EnsorEnchantments;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Displacement / Flaming Rebuke / Chilling Rebuke, including original proc gating and armor durability. */
public final class RebukeRuntime {
    private static final Map<Entity, Integer> PENDING_FIRE = new LinkedHashMap<>();

    public static void onPostHurt(LivingEntity wearer, Entity attacker) {
        if (!(attacker instanceof LivingEntity)) return;
        tryArmorRebuke(wearer, attacker, "displacement");
        tryArmorRebuke(wearer, attacker, "fire_rebuke");
        tryArmorRebuke(wearer, attacker, "frost_rebuke");
    }

    private static void tryArmorRebuke(LivingEntity wearer, Entity attacker, String enchantment) {
        int max = EnsorEnchantments.equipped(wearer, enchantment);
        if (max <= 0) return;
        int chance = EnsorConfig.integer(enchantment + ".effect_chance", 20);
        if (wearer.getRandom().nextInt(100) >= chance * max) return;
        apply(wearer, attacker, enchantment, max);
        damageRandomEnchantedArmor(wearer, enchantment);
    }

    public static void onShieldBlock(LivingEntity wearer, Entity attacker, ItemStack shield) {
        if (!(attacker instanceof LivingEntity)) return;
        for (String enchantment : new String[]{"displacement", "fire_rebuke", "frost_rebuke"}) {
            int level = EnsorEnchantments.level(shield, wearer.level(), enchantment);
            if (level > 0 && wearer.getRandom().nextInt(100) < EnsorConfig.integer(enchantment + ".effect_chance", 20) * level) {
                apply(wearer, attacker, enchantment, level);
            }
        }
    }

    private static void apply(LivingEntity wearer, Entity attacker, String enchantment, int level) {
        switch (enchantment) {
            case "displacement" -> displacement(wearer, attacker, level);
            case "fire_rebuke" -> fire(wearer, attacker, level);
            case "frost_rebuke" -> frost(wearer, attacker, level);
        }
    }

    private static boolean mobsMayAffectPlayer(LivingEntity wearer, Entity attacker, String key) {
        return wearer instanceof Player || !(attacker instanceof Player) || EnsorConfig.bool(key, false);
    }

    private static void displacement(LivingEntity wearer, Entity attacker, int level) {
        if (!(attacker instanceof LivingEntity living)) return;
        if (!mobsMayAffectPlayer(wearer, attacker, "displacement.mobs_teleport_players")) return;
        // 1.20 used Entity.canChangeDimensions() as a teleport-eligibility guard.
        // In 1.21.1 it takes source/destination levels; Displacement is same-level,
        // so pass the current level for both sides to preserve that gate.
        if (living.hasEffect(CoreContent.ENDERFERENCE) || !living.canChangeDimensions(living.level(), living.level())) return;

        int radius = 16 * level;
        int bound = radius * 2 + 1;
        BlockPos base = BlockPos.containing(attacker.getX(), attacker.getY(), attacker.getZ());
        BlockPos target = base.offset(-radius + wearer.getRandom().nextInt(bound), wearer.getRandom().nextInt(8), -radius + wearer.getRandom().nextInt(bound));
        if (attacker.isPassenger()) attacker.stopRiding();
        attacker.teleportTo(target.getX() + 0.5D, target.getY(), target.getZ() + 0.5D);
        attacker.fallDistance = 0.0F;
        attacker.playSound(SoundEvents.ENDERMAN_TELEPORT, 1.0F, 1.0F);
        if (attacker.level() instanceof ServerLevel server) {
            for (int i = 0; i < 3 * level; i++) server.sendParticles(ParticleTypes.PORTAL,
                    attacker.getX() + wearer.getRandom().nextDouble(), attacker.getY() + 1.0D + wearer.getRandom().nextDouble(), attacker.getZ() + wearer.getRandom().nextDouble(),
                    1, 0, 0, 0, 0);
        }
    }

    private static void fire(LivingEntity wearer, Entity attacker, int level) {
        LivingEntity living = (LivingEntity) attacker;
        if (mobsMayAffectPlayer(wearer, attacker, "fire_rebuke.mobs_knockback_players")) {
            living.knockback(0.5F * level, wearer.getX() - attacker.getX(), wearer.getZ() - attacker.getZ());
        }
        PENDING_FIRE.put(attacker, 1 + wearer.getRandom().nextInt(3 * level));
        if (attacker.level() instanceof ServerLevel server) {
            for (int i = 0; i < 3 * level; i++) server.sendParticles(ParticleTypes.FLAME,
                    attacker.getX() + wearer.getRandom().nextDouble(), attacker.getY() + 1.0D + wearer.getRandom().nextDouble(), attacker.getZ() + wearer.getRandom().nextDouble(),
                    1, 0, 0, 0, 0);
        }
    }

    private static void frost(LivingEntity wearer, Entity attacker, int level) {
        LivingEntity living = (LivingEntity) attacker;
        if (mobsMayAffectPlayer(wearer, attacker, "frost_rebuke.mobs_knockback_players")) {
            living.knockback(0.5F * level, wearer.getX() - attacker.getX(), wearer.getZ() - attacker.getZ());
        }
        int duration = 20 + 20 * wearer.getRandom().nextInt(3 * level);
        if (attacker.isOnFire()) attacker.clearFire();
        living.addEffect(new MobEffectInstance(CoreContent.CHILLED, duration, level - 1, false, false));
        if (attacker.level() instanceof ServerLevel server) {
            for (int i = 0; i < 3 * level; i++) server.sendParticles(CoreContent.FROST,
                    attacker.getX() + wearer.getRandom().nextDouble(), attacker.getY() + 1.0D + wearer.getRandom().nextDouble(), attacker.getZ() + wearer.getRandom().nextDouble(),
                    1, 0, 0, 0, 0);
        }
    }

    private static void damageRandomEnchantedArmor(LivingEntity wearer, String enchantment) {
        List<EquipmentSlot> matching = new ArrayList<>();
        for (EquipmentSlot slot : new EquipmentSlot[]{EquipmentSlot.HEAD, EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET, EquipmentSlot.BODY}) {
            if (EnsorEnchantments.level(wearer.getItemBySlot(slot), wearer.level(), enchantment) > 0) matching.add(slot);
        }
        if (matching.isEmpty()) return;
        EquipmentSlot slot = matching.get(wearer.getRandom().nextInt(matching.size()));
        wearer.getItemBySlot(slot).hurtAndBreak(2, wearer, slot);
    }

    public static void flushPendingFire() {
        if (PENDING_FIRE.isEmpty()) return;
        PENDING_FIRE.forEach((entity, seconds) -> {
            if (!entity.isRemoved()) entity.setRemainingFireTicks(seconds * 20);
        });
        PENDING_FIRE.clear();
    }

    private RebukeRuntime() {}
}
