/*******************************************************************************
 * ArmorStandPet - Fabric port
 * Optional pet mortality for Minecraft 26.2
 *******************************************************************************/
package io.github.kyzderp.armorstandpet.combat;

import io.github.kyzderp.armorstandpet.ASPetMod;
import io.github.kyzderp.armorstandpet.entity.PetArmorStandEntity;
import io.github.kyzderp.armorstandpet.scheduler.TickScheduler;
import io.github.kyzderp.armorstandpet.struct.OwnerToPet;
import io.github.kyzderp.armorstandpet.types.Pet;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.particles.ItemParticleOption;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

/**
 * Keeps the legacy invincible behavior by default, but can give an individual
 * pet a normal 20-point health pool. Vulnerable pets use Minecraft's normal
 * armor, armor-toughness, armor-enchantment and equipment-durability logic.
 * A short ten-tick hurt cooldown prevents rapid multi-hit sources from
 * deleting all health during one server tick.
 */
public final class PetMortalityController
{
	public static final float MAX_HEALTH = 20.0F;
	private static final long HURT_COOLDOWN_TICKS = 10L;
	private static final Map<UUID, Long> NEXT_DAMAGE_TICK = new HashMap<>();

	private PetMortalityController()
	{
	}

	/** Called by PetArmorStandEntity.hurtServer. */
	public static boolean hurt(PetArmorStandEntity stand, ServerLevel level,
			DamageSource source, float amount)
	{
		if (stand == null || stand.isRemoved() || amount <= 0.0F)
			return false;

		String owner = stand.getOwner();
		if (owner == null || owner.isEmpty())
			return false;

		String worldName = level.dimension().identifier().toString();
		Pet pet = OwnerToPet.get(worldName, owner);
		// Until a pet is fully registered, preserve the original safe behavior.
		if (pet == null || pet.invincible || pet.mortalDead || pet.getStand() != stand)
			return false;

		long now = level.getGameTime();
		long next = NEXT_DAMAGE_TICK.getOrDefault(stand.getUUID(), 0L);
		if (now < next)
			return false;
		NEXT_DAMAGE_TICK.put(stand.getUUID(), now + HURT_COOLDOWN_TICKS);

		float appliedDamage = Math.max(0.0F, stand.applyPetDefenses(source, amount));
		if (appliedDamage <= 0.0F)
			return true;

		float remaining = Math.max(0.0F, stand.getHealth() - appliedDamage);
		stand.setHealth(remaining);
		if (remaining <= 0.0F)
			kill(pet, stand, source);
		return true;
	}

	/**
	 * Performs a real LivingEntity death and then invokes the same permanent
	 * deletion path as /aspet delete. This removes the entity, both lookup maps,
	 * and the saved pet entry, so no command or lifecycle handler can revive it.
	 */
	private static void kill(Pet pet, PetArmorStandEntity stand, DamageSource source)
	{
		NEXT_DAMAGE_TICK.remove(stand.getUUID());
		OwnerAttackCombatController.disable(pet);
		TickScheduler.cancelPetTasks(pet);
		pet.isBusy = false;

		ServerLevel level = stand.serverLevel();
		ServerPlayer owner = levelPlayer(level, pet.getOwner());
		playVanillaBreakEffects(level, stand);
		stand.setHealth(0.0F);
		stand.die(source);
		pet.delete(true, true);

		if (owner != null)
			ASPetMod.inform(owner, "Your armor stand pet has died permanently. Create a new pet to replace it.");
	}

	/** Reproduces the vanilla armor stand's break sound and item-fragment burst. */
	private static void playVanillaBreakEffects(ServerLevel level, PetArmorStandEntity stand)
	{
		level.playSound(null, stand.getX(), stand.getY(), stand.getZ(),
				SoundEvents.ARMOR_STAND_BREAK, stand.getSoundSource(), 1.0F, 1.0F);
		level.sendParticles(
				new ItemParticleOption(ParticleTypes.ITEM, new ItemStack(Items.ARMOR_STAND)),
				stand.getX(), stand.getY() + (double) stand.getBbHeight() / 1.5D, stand.getZ(),
				10, 0.0D, 0.0D, 0.0D, 0.05D);
	}

	/** Removes dead entries written by the earlier revivable-death build. */
	public static void purgeLegacyDeadPets()
	{
		List<Pet> deadPets = new ArrayList<>();
		for (Map<String, Pet> world : OwnerToPet.getAll().values())
		{
			for (Pet pet : new ArrayList<>(world.values()))
			{
				if (pet != null && pet.getStand() != null
						&& (pet.mortalDead || pet.getStand().isDeadOrDying()))
					deadPets.add(pet);
			}
		}

		for (Pet pet : deadPets)
		{
			OwnerAttackCombatController.disable(pet);
			TickScheduler.cancelPetTasks(pet);
			pet.delete(true, true);
		}
	}

	private static ServerPlayer levelPlayer(ServerLevel level, String name)
	{
		return level.getServer().getPlayerList().getPlayerByName(name);
	}

	/** Applies a mode change only to an existing, living pet. */
	public static boolean setInvincible(Pet pet, ServerPlayer owner, boolean invincible)
	{
		if (pet == null || owner == null || pet.getStand() == null)
			return false;

		PetArmorStandEntity stand = pet.getStand();
		if (pet.mortalDead || stand.isRemoved() || stand.isDeadOrDying())
			return false;

		pet.mortalDead = false;
		pet.invincible = invincible;
		pet.isBusy = false;
		NEXT_DAMAGE_TICK.remove(stand.getUUID());
		stand.setHealth(MAX_HEALTH);
		pet.teleportTo(owner);
		ASPetMod.saveAllPets();
		return true;
	}
}
