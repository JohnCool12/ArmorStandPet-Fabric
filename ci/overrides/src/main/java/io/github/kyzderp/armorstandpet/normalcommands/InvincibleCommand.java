/*******************************************************************************
 * ArmorStandPet - Fabric port
 * Per-pet invincibility toggle for Minecraft 26.2
 *******************************************************************************/
package io.github.kyzderp.armorstandpet.normalcommands;

import io.github.kyzderp.armorstandpet.ASPetMod;
import io.github.kyzderp.armorstandpet.combat.PetMortalityController;
import io.github.kyzderp.armorstandpet.struct.OwnerToPet;
import io.github.kyzderp.armorstandpet.types.Pet;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.server.level.ServerPlayer;

public class InvincibleCommand extends BaseCommand
{
	public InvincibleCommand()
	{
		super("invincible");
		this.usage = "/aspet invincible <on|off>";
		this.description = "Toggle pet invincibility or give it 20 health.";
	}

	@Override
	public void run(CommandSourceStack sender, String[] args)
	{
		ServerPlayer player = sender.getPlayer();
		if (player == null)
			return;

		Pet pet = OwnerToPet.get(player.level().dimension().identifier().toString(),
				player.getName().getString());
		if (pet == null)
			return;

		if (args.length == 1)
		{
			String status;
			if (pet.mortalDead)
				status = "\u00A7cDEAD";
			else if (pet.invincible)
				status = "\u00A7aINVINCIBLE";
			else
				status = "\u00A7eVULNERABLE\u00A77 ("
						+ Math.max(0, Math.round(pet.getStand().getHealth())) + "/20 health)";
			ASPetMod.inform(sender, "Pet status: " + status
					+ "\u00A77. Usage: /aspet invincible <on|off>");
			return;
		}

		if (args.length != 2)
		{
			this.error(sender, "Usage: " + this.usage);
			return;
		}

		boolean invincible;
		if (args[1].equalsIgnoreCase("on"))
			invincible = true;
		else if (args[1].equalsIgnoreCase("off"))
			invincible = false;
		else
		{
			this.error(sender, "Usage: " + this.usage);
			return;
		}

		if (!PetMortalityController.setInvincible(pet, player, invincible))
		{
			this.error(sender, "Unable to change your pet's invincibility mode.");
			return;
		}

		if (invincible)
			ASPetMod.inform(sender, "Pet invincibility is now \u00A7aON\u00A77. Health restored to 20.");
		else
			ASPetMod.inform(sender, "Pet invincibility is now \u00A7cOFF\u00A77. Your pet has 20 health.");
	}
}
