package cofh.ensorcellation.fabric.runtime;

import cofh.ensorcellation.fabric.config.EnsorConfig;
import cofh.ensorcellation.fabric.enchantment.EnsorEnchantments;
import net.minecraft.core.component.DataComponents;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.animal.Animal;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.monster.Creeper;
import net.minecraft.world.entity.monster.Skeleton;
import net.minecraft.world.entity.monster.WitherSkeleton;
import net.minecraft.world.entity.monster.Zombie;
import net.minecraft.world.entity.monster.piglin.AbstractPiglin;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.component.ResolvableProfile;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;

/** Hunter, Outlaw, Vorpal-head and death-drop behavior from CommonEvents. */
public final class LootRuntime {
    public static void onDeath(ServerLevel level, LivingEntity dead, DamageSource source) {
        if (!(source.getEntity() instanceof Player player)) return;

        int hunter = EnsorEnchantments.held(player, "hunter");
        if (hunter > 0 && dead instanceof Animal) rerollAnimalLoot(level, dead, source, player, hunter);

        int outlaw = EnsorEnchantments.held(player, "damage_villager");
        if (outlaw > 0 && EnsorConfig.bool("damage_villager.emerald_drops", true) && CombatRuntime.isVillager(dead)) {
            int count = Mth.nextInt(player.getRandom(), 0, outlaw);
            if (count > 0) spawn(level, dead, new ItemStack(Items.EMERALD, count), 0);
        }

        int vorpal = EnsorEnchantments.held(player, "vorpal");
        if (vorpal > 0 && dead.getRandom().nextInt(100) < EnsorConfig.integer("vorpal.head_base", 10) + EnsorConfig.integer("vorpal.head_per_level", 10) * vorpal) {
            ItemStack head = headFor(dead);
            if (!head.isEmpty()) spawn(level, dead, head, 10);
        }
    }

    private static void rerollAnimalLoot(ServerLevel level, LivingEntity dead, DamageSource source, Player player, int enchantLevel) {
        net.minecraft.resources.ResourceKey<LootTable> key = dead.getLootTable();
        LootTable table = level.getServer().reloadableRegistries().getLootTable(key);
        LootParams params = new LootParams.Builder(level)
                .withParameter(LootContextParams.THIS_ENTITY, dead)
                .withParameter(LootContextParams.ORIGIN, dead.position())
                .withParameter(LootContextParams.DAMAGE_SOURCE, source)
                .withParameter(LootContextParams.LAST_DAMAGE_PLAYER, player)
                .withOptionalParameter(LootContextParams.ATTACKING_ENTITY, source.getEntity())
                .withOptionalParameter(LootContextParams.DIRECT_ATTACKING_ENTITY, source.getDirectEntity())
                .withLuck(player.getLuck())
                .create(LootContextParamSets.ENTITY);

        int chance = EnsorConfig.integer("hunter.effect_chance", 50);
        for (int i = 0; i < enchantLevel; i++) {
            if (player.getRandom().nextInt(100) < chance) {
                for (ItemStack stack : table.getRandomItems(params)) spawn(level, dead, stack, 0);
            }
        }
    }

    private static ItemStack headFor(LivingEntity dead) {
        if (dead instanceof ServerPlayer player) {
            ItemStack stack = new ItemStack(Items.PLAYER_HEAD);
            stack.set(DataComponents.PROFILE, new ResolvableProfile(player.getGameProfile()));
            return stack;
        }
        if (dead instanceof Skeleton) return new ItemStack(Items.SKELETON_SKULL);
        if (dead instanceof WitherSkeleton) return new ItemStack(Items.WITHER_SKELETON_SKULL);
        if (dead instanceof Zombie) return new ItemStack(Items.ZOMBIE_HEAD);
        if (dead instanceof Creeper) return new ItemStack(Items.CREEPER_HEAD);
        if (dead instanceof AbstractPiglin) return new ItemStack(Items.PIGLIN_HEAD);
        return ItemStack.EMPTY;
    }

    private static void spawn(ServerLevel level, LivingEntity dead, ItemStack stack, int pickupDelay) {
        ItemEntity item = new ItemEntity(level, dead.getX(), dead.getY(), dead.getZ(), stack);
        if (pickupDelay > 0) item.setPickUpDelay(pickupDelay);
        level.addFreshEntity(item);
    }

    private LootRuntime() {}
}
