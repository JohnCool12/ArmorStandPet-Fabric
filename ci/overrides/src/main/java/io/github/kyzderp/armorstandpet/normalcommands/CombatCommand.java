/*******************************************************************************
 * ArmorStandPet - Fabric port
 * Per-pet combat toggle for Minecraft 26.2
 *******************************************************************************/
package io.github.kyzderp.armorstandpet.normalcommands;

import io.github.kyzderp.armorstandpet.ASPetMod;
import io.github.kyzderp.armorstandpet.combat.OwnerAttackCombatController;
import io.github.kyzderp.armorstandpet.struct.OwnerToPet;
import io.github.kyzderp.armorstandpet.types.Pet;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.server.level.ServerPlayer;

public class CombatCommand extends BaseCommand
{
	public CombatCommand()
	{
		super("combat");
		this.usage = "/aspet combat <on|off>";
		this.description = "Enable or disable attacking mobs that you hit.";
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
			ASPetMod.inform(sender, "Combat is currently "
					+ (pet.combatEnabled ? "\u00A7aON" : "\u00A7cOFF")
					+ "\u00A77. Usage: /aspet combat <on|off>");
			return;
		}

		if (args.length != 2)
		{
			this.error(sender, "Usage: " + this.usage);
			return;
		}

		if (args[1].equalsIgnoreCase("on"))
		{
			pet.combatEnabled = true;
			ASPetMod.saveAllPets();
			ASPetMod.inform(sender, "Pet combat is now \u00A7aON\u00A77. Your pet will attack mobs that you hit.");
			return;
		}

		if (args[1].equalsIgnoreCase("off"))
		{
			pet.combatEnabled = false;
			OwnerAttackCombatController.disable(pet);
			ASPetMod.saveAllPets();
			ASPetMod.inform(sender, "Pet combat is now \u00A7cOFF\u00A77.");
			return;
		}

		this.error(sender, "Usage: " + this.usage);
	}
}
