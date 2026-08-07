/*******************************************************************************
 * ArmorStandPet - Fabric port
 * Original Bukkit plugin (c) 2016, 2017 Hannah Chu
 *******************************************************************************/
package io.github.kyzderp.armorstandpet.client;

import net.minecraft.client.renderer.entity.ArmorStandRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.state.ArmorStandRenderState;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.decoration.ArmorStand;

/**
 * Uses the vanilla armor-stand renderer while preserving vanilla's equipment
 * special cases for a custom registered ArmorStand subclass.
 */
public final class PetArmorStandRenderer extends ArmorStandRenderer
{
	public PetArmorStandRenderer(EntityRendererProvider.Context context)
	{
		super(context);
	}

	@Override
	public void extractRenderState(ArmorStand entity, ArmorStandRenderState state, float partialTick)
	{
		super.extractRenderState(entity, state, partialTick);

		/*
		 * Minecraft 26.2's armor and held-item layers special-case the vanilla
		 * EntityTypes.ARMOR_STAND identity. A small custom armor-stand entity is
		 * otherwise treated as a generic baby humanoid, which selects baby armor
		 * textures and offsets held items into the body. The render state identity
		 * is used only by rendering; the actual entity remains our custom type.
		 */
		state.entityType = EntityTypes.ARMOR_STAND;
	}
}
