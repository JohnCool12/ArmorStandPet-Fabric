/*******************************************************************************
 * ArmorStandPet - Fabric port
 * Optional pet mortality for Minecraft 26.2
 *******************************************************************************/
package io.github.kyzderp.armorstandpet.combat;

import io.github.kyzderp.armorstandpet.ASPetMod;
import io.github.kyzderp.armorstandpet.entity.PetArmorStandEntity;
import io.github.kyzderp.armorstandpet.entity.StandFactory;
import io.github.kyzderp.armorstandpet.scheduler.TickScheduler;
import io.github.kyzderp.armorstandpet.struct.OwnerToPet;
import io.github.kyzderp.armorstandpet.struct.StandToOwner;
import io.github.kyzderp.armorstandpet.types.Pet;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageSource;

/**
 * Keeps the legacy invincible behavior by default, but can give an individual
 * pet a normal 20-point health pool. Damage is intentionally simple and
 * predictable: armor does not alter the pool, and a short ten-tick hurt
 * cooldown prevents rapid multi-hit sources from deleting all health in one
 * server tick.
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

		float remaining = Math.max(0.0F, stand.getHealth() - amount);
		stand.setHealth(remaining);
		if (remaining <= 0.0F)
			kill(pet, stand, worldName);
		return true;
	}

	private static void kill(Pet pet, PetArmorStandEntity stand, String worldName)
	{
		NEXT_DAMAGE_TICK.remove(stand.getUUID());
		OwnerAttackCombatController.disable(pet);
		TickScheduler.cancelPetTasks(pet);
		pet.isBusy = false;
		pet.mortalDead = true;
		StandToOwner.remove(worldName, stand);
		stand.setHealth(0.0F);
		stand.discard();

		ServerPlayer owner = levelPlayer(stand.serverLevel(), pet.getOwner());
		if (owner != null)
			ASPetMod.inform(owner, "Your armor stand pet has died. Use /aspet invincible on or off to revive it.");
		ASPetMod.saveAllPets();
	}

	private static ServerPlayer levelPlayer(ServerLevel level, String name)
	{
		return level.getServer().getPlayerList().getPlayerByName(name);
	}

	/**
	 * Applies a mode change. A dead pet is rebuilt from its retained appearance
	 * and equipment, then placed at its owner with a full 20-point health pool.
	 */
	public static boolean setInvincible(Pet pet, ServerPlayer owner, boolean invincible)
	{
		if (pet == null || owner == null || pet.getStand() == null)
			return false;

		PetArmorStandEntity stand = pet.getStand();
		String oldWorld = stand.serverLevel().dimension().identifier().toString();
		if (pet.mortalDead || stand.isRemoved())
		{
			StandToOwner.remove(oldWorld, stand);
			stand = StandFactory.respawnFrom(stand);
			pet.setStand(stand);
			StandToOwner.put(oldWorld, stand, pet.getOwner());
		}

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
