/*******************************************************************************
 * ArmorStandPet - Fabric port
 * Original Bukkit plugin (c) 2016, 2017 Hannah Chu
 *******************************************************************************/
package io.github.kyzderp.armorstandpet.entity;

import net.fabricmc.fabric.api.object.builder.v1.entity.FabricDefaultAttributeRegistry;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.entity.decoration.ArmorStand;

public class ModEntities
{
	private static final Identifier PET_ID = Identifier.fromNamespaceAndPath("armorstandpet", "pet");
	private static final ResourceKey<EntityType<?>> PET_KEY = ResourceKey.create(Registries.ENTITY_TYPE, PET_ID);

	// Same base dimensions and tracking settings used by the prior 26.2 port.
	public static final EntityType<PetArmorStandEntity> PET_ARMOR_STAND = Registry.register(
			BuiltInRegistries.ENTITY_TYPE,
			PET_KEY,
			EntityType.Builder.of(PetArmorStandEntity::new, MobCategory.MISC)
					.sized(0.5F, 1.975F)
					.clientTrackingRange(10)
					.updateInterval(3)
					.build(PET_KEY));

	public static void init()
	{
		// PetArmorStandEntity extends LivingEntity through ArmorStand. Minecraft
		// 26.2 requires every custom living entity type to have an AttributeSupplier
		// registered before its constructor runs. Reuse vanilla armor-stand defaults.
		FabricDefaultAttributeRegistry.register(PET_ARMOR_STAND, ArmorStand.createAttributes().build());
	}
}
