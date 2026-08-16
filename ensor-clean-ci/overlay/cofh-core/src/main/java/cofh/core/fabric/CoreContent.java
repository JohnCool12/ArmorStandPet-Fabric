package cofh.core.fabric;

import cofh.core.fabric.block.GlossedMagmaBlock;
import cofh.core.fabric.effect.ChilledEffect;
import cofh.core.fabric.effect.EnderferenceEffect;
import net.fabricmc.fabric.api.particle.v1.FabricParticleTypes;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.particles.SimpleParticleType;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockBehaviour;

public final class CoreContent {
    public static SimpleParticleType FROST;
    public static Holder<MobEffect> CHILLED;
    public static Holder<MobEffect> ENDERFERENCE;
    public static Block GLOSSED_MAGMA;

    public static void register() {
        FROST = Registry.register(BuiltInRegistries.PARTICLE_TYPE, id("frost"), FabricParticleTypes.simple());

        ChilledEffect chilled = (ChilledEffect) new ChilledEffect(FROST)
                .addAttributeModifier(Attributes.MOVEMENT_SPEED, id("effect.chilled_movement_speed"), -0.10D, AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL)
                .addAttributeModifier(Attributes.ATTACK_SPEED, id("effect.chilled_attack_speed"), -0.20D, AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL);
        CHILLED = Registry.registerForHolder(BuiltInRegistries.MOB_EFFECT, id("chilled"), chilled);
        ENDERFERENCE = Registry.registerForHolder(BuiltInRegistries.MOB_EFFECT, id("enderference"), new EnderferenceEffect());

        GLOSSED_MAGMA = Registry.register(BuiltInRegistries.BLOCK, id("glossed_magma"),
                new GlossedMagmaBlock(BlockBehaviour.Properties.ofFullCopy(Blocks.MAGMA_BLOCK).randomTicks()));
    }

    public static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(CoFHCoreFabric.MOD_ID, path);
    }

    private CoreContent() {}
}
