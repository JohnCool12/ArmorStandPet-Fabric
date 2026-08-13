/*******************************************************************************
 * ArmorStandPet - Fabric port
 * Original Bukkit plugin (c) 2016, 2017 Hannah Chu
 *******************************************************************************/
package io.github.kyzderp.armorstandpet.client;

import io.github.kyzderp.armorstandpet.entity.ModEntities;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.rendering.v1.EntityRendererRegistry;

public class ASPetModClient implements ClientModInitializer
{
	@Override
	public void onInitializeClient()
	{
		EntityRendererRegistry.register(ModEntities.PET_ARMOR_STAND, PetArmorStandRenderer::new);
	}
}
