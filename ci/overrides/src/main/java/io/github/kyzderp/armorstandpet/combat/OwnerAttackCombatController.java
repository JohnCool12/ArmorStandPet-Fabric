/*******************************************************************************
 * ArmorStandPet - Fabric port
 * Owner-directed combat for Minecraft 26.2
 *******************************************************************************/
package io.github.kyzderp.armorstandpet.combat;

import io.github.kyzderp.armorstandpet.entity.PetArmorStandEntity;
import io.github.kyzderp.armorstandpet.scheduler.TickScheduler;
import io.github.kyzderp.armorstandpet.struct.OwnerToPet;
import io.github.kyzderp.armorstandpet.types.Pet;
import io.github.kyzderp.armorstandpet.util.EulerAngle;
import io.github.kyzderp.armorstandpet.util.Pos;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.UUID;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;

/**
 * Gives a pet one intentionally narrow wolf-like combat behavior:
 * when its owner attacks a mob, an explicitly combat-enabled pet chases and
 * attacks that same mob.
 *
 * This class deliberately does not listen for the owner taking damage, so the
 * pet never retaliates merely because a mob hurt its owner.
 */
public final class OwnerAttackCombatController
{
	private static final float ATTACK_DAMAGE = 4.0F;
	// The previous 10-tick interval was 0.5 seconds. Twenty-five ticks is
	// exactly 2.5 times slower, or one attack every 1.25 seconds.
	private static final long ATTACK_COOLDOWN_TICKS = 25L;
	private static final long ATTACK_ANIMATION_TICKS = 7L;
	private static final long PURSUIT_TIMEOUT_TICKS = 300L;
	private static final double ATTACK_RANGE_SQUARED = 4.0D;
	private static final double MAX_PURSUIT_RANGE_SQUARED = 1600.0D;
	private static final EulerAngle LEFT_ARM_ATTACK_POSE = new EulerAngle(-0.65D, 0.0D, -0.1D);

	private static final Map<UUID, AttackState> ACTIVE_ATTACKS = new HashMap<>();
	private static boolean registered;

	private OwnerAttackCombatController()
	{
	}

	public static synchronized void register()
	{
		if (registered)
			return;
		registered = true;
		ServerTickEvents.END_SERVER_TICK.register(OwnerAttackCombatController::onServerTick);
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> clearAll());
	}

	/**
	 * Called only from the existing player attack callback. Players, armor
	 * stands, projectiles and other non-mob entities are intentionally ignored.
	 */
	public static void onOwnerAttack(Player player, Level level, Entity attackedEntity)
	{
		if (level.isClientSide())
			return;
		if (!(player instanceof ServerPlayer owner))
			return;
		if (!(attackedEntity instanceof Mob target))
			return;
		if (!target.isAlive() || target.isRemoved())
			return;

		String worldName = level.dimension().identifier().toString();
		Pet pet = OwnerToPet.get(worldName, owner.getName().getString());
		if (pet == null || !pet.combatEnabled || pet.isSitting)
			return;

		PetArmorStandEntity stand = pet.getStand();
		if (stand == null || stand.isDeadOrDying())
			return;

		// Combat is an imperative order. Cancel any queued walking, chasing,
		// delayed callback or name-revert task belonging to this pet so an
		// existing follow/command chain cannot continue moving it afterward.
		TickScheduler.cancelPetTasks(pet);
		restorePetName(pet, stand);
		pet.walkFlat();
		pet.isBusy = true;

		long now = level.getGameTime();
		ACTIVE_ATTACKS.put(stand.getUUID(),
				new AttackState(pet, target, now + PURSUIT_TIMEOUT_TICKS, now));
	}

	/** Cancels an active pursuit when /aspet combat off is used. */
	public static void disable(Pet pet)
	{
		if (pet == null)
			return;
		PetArmorStandEntity stand = pet.getStand();
		if (stand == null)
			return;
		AttackState state = ACTIVE_ATTACKS.remove(stand.getUUID());
		if (state != null)
			release(state);
	}

	private static void onServerTick(MinecraftServer server)
	{
		Iterator<Map.Entry<UUID, AttackState>> iterator = ACTIVE_ATTACKS.entrySet().iterator();
		while (iterator.hasNext())
		{
			Map.Entry<UUID, AttackState> entry = iterator.next();
			AttackState state = entry.getValue();
			Pet pet = state.pet;
			PetArmorStandEntity stand = pet.getStand();
			Mob target = state.target;

			if (!pet.combatEnabled
					|| stand == null || stand.isDeadOrDying()
					|| !stand.getUUID().equals(entry.getKey())
					|| target == null || target.isRemoved() || !target.isAlive()
					|| pet.isSitting)
			{
				finish(iterator, state);
				continue;
			}

			ServerLevel level = stand.serverLevel();
			if (target.level() != level)
			{
				finish(iterator, state);
				continue;
			}

			long now = level.getGameTime();
			if (now > state.expiresAtTick)
			{
				finish(iterator, state);
				continue;
			}

			if (state.animationResetTick > 0L && now >= state.animationResetTick)
			{
				pet.walkFlat();
				state.animationResetTick = 0L;
			}

			double distanceSquared = stand.distanceToSqr(target);
			if (distanceSquared > MAX_PURSUIT_RANGE_SQUARED)
			{
				finish(iterator, state);
				continue;
			}

			Pos targetPosition = new Pos(level, target.getX(), target.getY(), target.getZ(),
					target.getYRot(), target.getXRot());
			pet.faceLoc(targetPosition);

			if (distanceSquared > ATTACK_RANGE_SQUARED)
			{
				// Keep the original pet movement and animation instead of introducing
				// a second navigation system. Stationary pet types remain stationary.
				if (pet.isMobile)
				{
					pet.takeStep();
					pet.animateWalk();
				}
				continue;
			}

			// Keep the lifted arm visible for several ticks instead of flattening
			// the pose immediately on the tick following a hit.
			if (state.animationResetTick == 0L)
				pet.walkFlat();
			if (now < state.nextAttackTick)
				continue;

			stand.setLeftArmPose(LEFT_ARM_ATTACK_POSE);
			stand.swing(InteractionHand.MAIN_HAND);
			target.hurtServer(level, level.damageSources().mobAttack(stand), ATTACK_DAMAGE);
			state.animationResetTick = now + ATTACK_ANIMATION_TICKS;
			state.nextAttackTick = now + ATTACK_COOLDOWN_TICKS;

			if (!target.isAlive() || target.isRemoved())
				finish(iterator, state);
		}
	}

	private static void restorePetName(Pet pet, PetArmorStandEntity stand)
	{
		if (pet.getName().isEmpty())
		{
			stand.setCustomNameString("");
			stand.setCustomNameVisible(false);
		}
		else
		{
			stand.setCustomNameString(pet.getName());
			stand.setCustomNameVisible(true);
		}
	}

	private static void finish(Iterator<Map.Entry<UUID, AttackState>> iterator, AttackState state)
	{
		iterator.remove();
		release(state);
	}

	private static void release(AttackState state)
	{
		state.pet.isBusy = false;
		if (state.pet.getStand() != null && !state.pet.getStand().isDeadOrDying())
			state.pet.walkFlat();
	}

	private static void clearAll()
	{
		for (AttackState state : ACTIVE_ATTACKS.values())
			state.pet.isBusy = false;
		ACTIVE_ATTACKS.clear();
	}

	private static final class AttackState
	{
		private final Pet pet;
		private final Mob target;
		private final long expiresAtTick;
		private long nextAttackTick;
		private long animationResetTick;

		private AttackState(Pet pet, Mob target, long expiresAtTick, long nextAttackTick)
		{
			this.pet = pet;
			this.target = target;
			this.expiresAtTick = expiresAtTick;
			this.nextAttackTick = nextAttackTick;
		}
	}
}
