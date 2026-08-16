package cofh.ensorcellation.fabric.runtime;

import cofh.ensorcellation.fabric.EnsorcellationFabric;
import cofh.ensorcellation.fabric.enchantment.EnsorEnchantments;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

/** Original shield-specific Ensorcellation behavior. */
public final class ShieldRuntime {
    private static final ResourceLocation BULWARK_ID = id("bulwark");
    private static final ResourceLocation PHALANX_ID = id("phalanx");

    public static void tick(LivingEntity entity) {
        AttributeInstance knockback = entity.getAttribute(Attributes.KNOCKBACK_RESISTANCE);
        AttributeInstance speed = entity.getAttribute(Attributes.MOVEMENT_SPEED);
        if (knockback != null) knockback.removeModifier(BULWARK_ID);
        if (speed != null) speed.removeModifier(PHALANX_ID);

        ItemStack stack = entity.getUseItem();
        // NeoForge's ToolActions.SHIELD_BLOCK has no direct Fabric equivalent.
        // While an item is actively in use, isBlocking() expresses the same gameplay
        // condition without hard-coding vanilla ShieldItem and therefore retains support
        // for modded items that participate in Minecraft's blocking behavior.
        if (stack.isEmpty() || !entity.isBlocking()) return;

        int bulwark = EnsorEnchantments.level(stack, entity.level(), "bulwark");
        if (bulwark > 0 && knockback != null) {
            knockback.addTransientModifier(new AttributeModifier(BULWARK_ID, 1.0D, AttributeModifier.Operation.ADD_VALUE));
        }
        int phalanx = EnsorEnchantments.level(stack, entity.level(), "phalanx");
        if (phalanx > 0 && speed != null) {
            speed.addTransientModifier(new AttributeModifier(PHALANX_ID, 1.25D * phalanx, AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL));
        }
    }

    public static void onBlocked(LivingEntity defender, DamageSource source, float blockedAmount) {
        if (blockedAmount <= 0.0F) return;
        Entity attacker = source.getEntity();
        if (attacker == null) return;
        ItemStack shield = defender.getUseItem();
        if (shield.isEmpty()) return;

        int thorns = vanillaEnchantmentLevel(defender, shield, net.minecraft.world.item.enchantment.Enchantments.THORNS);
        if (thorns > 0 && defender.getRandom().nextFloat() < 0.15F * thorns) {
            int damage = thorns > 10 ? thorns - 10 : 1 + defender.getRandom().nextInt(4);
            attacker.hurt(defender.damageSources().thorns(defender), damage);
        }

        RebukeRuntime.onShieldBlock(defender, attacker, shield);

        int bulwark = EnsorEnchantments.level(shield, defender.level(), "bulwark");
        if (bulwark > 0 && attacker instanceof Player player && player.getRandom().nextFloat() < 0.5F) {
            player.getCooldowns().addCooldown(player.getMainHandItem().getItem(), 100);
            player.level().broadcastEntityEvent(player, (byte) 30);
        }
    }

    private static int vanillaEnchantmentLevel(LivingEntity entity, ItemStack stack, net.minecraft.resources.ResourceKey<net.minecraft.world.item.enchantment.Enchantment> key) {
        var holder = entity.level().registryAccess().registryOrThrow(net.minecraft.core.registries.Registries.ENCHANTMENT).getHolderOrThrow(key);
        return net.minecraft.world.item.enchantment.EnchantmentHelper.getItemEnchantmentLevel(holder, stack);
    }

    private static ResourceLocation id(String path) { return ResourceLocation.fromNamespaceAndPath(EnsorcellationFabric.MOD_ID, path); }
    private ShieldRuntime() {}
}
