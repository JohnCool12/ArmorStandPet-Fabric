package com.kyanite.deeperdarker.content;

import com.kyanite.deeperdarker.DeeperDarker;
import com.kyanite.deeperdarker.content.entities.*;
import com.kyanite.deeperdarker.util.registry.DDDeferredRegister;
import com.kyanite.deeperdarker.util.registry.DDRegistryEntry;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;

public class DDEntities {
    public static final DDDeferredRegister<EntityType<?>> ENTITIES = DDDeferredRegister.create(Registries.ENTITY_TYPE, DeeperDarker.MOD_ID);

    // Fabric/vanilla 1.21.1 supports the no-argument build() path. Supplying the
    // mod ID string to build(String) asks vanilla's DataFixerUpper for a vanilla
    // schema entry and logs a misleading ERROR for every modded entity. Registry
    // identity is supplied by DDDeferredRegister below, so build() is correct here.
    public static final DDRegistryEntry<EntityType<DDBoat>> BOAT = ENTITIES.register("boat", () -> EntityType.Builder.<DDBoat>of(DDBoat::new, MobCategory.MISC).sized(1.375f, 0.5625f).clientTrackingRange(10).build());
    public static final DDRegistryEntry<EntityType<DDChestBoat>> CHEST_BOAT = ENTITIES.register("chest_boat", () -> EntityType.Builder.<DDChestBoat>of(DDChestBoat::new, MobCategory.MISC).sized(1.375f, 0.5625f).clientTrackingRange(10).build());

    public static final DDRegistryEntry<EntityType<AnglerFish>> ANGLER_FISH = ENTITIES.register("angler_fish", () -> EntityType.Builder.of(AnglerFish::new, MobCategory.WATER_CREATURE).sized(0.7f, 0.4f).clientTrackingRange(10).build());
    public static final DDRegistryEntry<EntityType<OvercastPot>> ANGER_POT = ENTITIES.register("anger_pot", () -> EntityType.Builder.of(OvercastPot::new, MobCategory.MONSTER).sized(1.25f, 0.9375f).eyeHeight(0.4f).clientTrackingRange(10).build());
    public static final DDRegistryEntry<EntityType<OvercastPot>> FEAR_POT = ENTITIES.register("fear_pot", () -> EntityType.Builder.of(OvercastPot::new, MobCategory.MONSTER).sized(0.75f, 1.9375f).eyeHeight(1.375f).clientTrackingRange(10).build());
    public static final DDRegistryEntry<EntityType<OvercastPot>> SORROW_POT = ENTITIES.register("sorrow_pot", () -> EntityType.Builder.of(OvercastPot::new, MobCategory.MONSTER).sized(0.75f, 1.2f).eyeHeight(0.8f).clientTrackingRange(10).build());
    public static final DDRegistryEntry<EntityType<SculkCentipede>> SCULK_CENTIPEDE = ENTITIES.register("sculk_centipede", () -> EntityType.Builder.of(SculkCentipede::new, MobCategory.MONSTER).sized(1f, 0.2f).clientTrackingRange(10).build());
    public static final DDRegistryEntry<EntityType<SculkLeech>> SCULK_LEECH = ENTITIES.register("sculk_leech", () -> EntityType.Builder.of(SculkLeech::new, MobCategory.MONSTER).sized(0.42f, 0.2f).clientTrackingRange(10).build());
    public static final DDRegistryEntry<EntityType<SculkSnapper>> SCULK_SNAPPER = ENTITIES.register("sculk_snapper", () -> EntityType.Builder.of(SculkSnapper::new, MobCategory.MONSTER).sized(0.65f, 0.65f).clientTrackingRange(10).build());
    public static final DDRegistryEntry<EntityType<Shattered>> SHATTERED = ENTITIES.register("shattered", () -> EntityType.Builder.of(Shattered::new, MobCategory.MONSTER).sized(0.7f, 2.0625f).clientTrackingRange(10).build());
    public static final DDRegistryEntry<EntityType<ShriekWorm>> SHRIEK_WORM = ENTITIES.register("shriek_worm", () -> EntityType.Builder.of(ShriekWorm::new, MobCategory.MONSTER).sized(1f, 5.7f).clientTrackingRange(10).build());
    public static final DDRegistryEntry<EntityType<Sludge>> SLUDGE = ENTITIES.register("sludge", () -> EntityType.Builder.of(Sludge::new, MobCategory.MONSTER).sized(0.52f, 0.52f).eyeHeight(0.325f).spawnDimensionsScale(4f).clientTrackingRange(10).build());
    public static final DDRegistryEntry<EntityType<Stalker>> STALKER = ENTITIES.register("stalker", () -> EntityType.Builder.of(Stalker::new, MobCategory.MONSTER).sized(0.9f, 4.3375f).eyeHeight(3.99f).clientTrackingRange(10).build());
}
