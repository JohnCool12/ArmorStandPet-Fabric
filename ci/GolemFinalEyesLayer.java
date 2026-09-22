package com.mcmoddev.golems.client.entity.layer;

import com.mcmoddev.golems.ExtraGolems;
import com.mcmoddev.golems.client.entity.GolemModel;
import com.mcmoddev.golems.data.GolemContainer;
import com.mcmoddev.golems.data.ResourcePair;
import com.mcmoddev.golems.data.model.Layer;
import com.mcmoddev.golems.entity.GolemBase;
import com.mojang.blaze3d.platform.NativeImage;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.LivingEntityRenderer;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.client.renderer.texture.DynamicTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.server.packs.resources.ResourceManager;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/**
 * Final eye pass for every Extra Golems model.
 *
 * Normal model layers can be rendered coplanar with texture/shader overlays. A
 * later overlay can therefore hide the tiny eye pixels even though the eyes
 * are still present in the model data. This layer re-renders each golem's own
 * configured eye layer last and expands it by a tiny amount to keep the eyes
 * visible without changing their texture, color, render type, or light rules.
 *
 * A few legacy models have their eye pixels baked into a full entity texture
 * instead of declaring a separate eye layer. For those models, an eye-only
 * dynamic texture is produced by masking that exact source texture with the
 * standard eye UV mask, preserving the model-specific eye pixels.
 */
public class GolemFinalEyesLayer<T extends GolemBase> extends RenderLayer<T, GolemModel<T>> {

    private static final ResourceLocation EYE_MASK = ResourceLocation.fromNamespaceAndPath(
            ExtraGolems.MODID, "textures/entity/golem/eyes.png");
    private static final float EYE_SURFACE_SCALE = 1.0015F;

    private static final Map<ResourceLocation, ResourceLocation> EMBEDDED_EYE_CACHE = new HashMap<>();
    private static ResourceManager cachedResourceManager;

    public GolemFinalEyesLayer(RenderLayerParent<T, GolemModel<T>> renderParent) {
        super(renderParent);
    }

    @Override
    public void render(PoseStack poseStack, MultiBufferSource bufferSource, int packedLight, T entity,
                       float limbSwing, float limbSwingAmount, float partialTicks, float ageInTicks,
                       float netHeadYaw, float headPitch) {
        final Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.player != null && entity.isInvisibleTo(minecraft.player)) {
            return;
        }

        final Optional<GolemContainer> oContainer = entity.getContainer();
        if (oContainer.isEmpty()) {
            return;
        }

        poseStack.pushPose();
        poseStack.scale(EYE_SURFACE_SCALE, EYE_SURFACE_SCALE, EYE_SURFACE_SCALE);

        final int packedOverlay = LivingEntityRenderer.getOverlayCoords(entity, 0.0F);
        boolean renderedConfiguredEyes = false;

        // Re-render the exact eye layer(s) declared by this golem's model. This
        // automatically preserves special eyes such as ender, glasses, white,
        // tinted, emissive, and any future data-driven eye variants.
        for (Layer layer : oContainer.get().getModel().get(entity.level().registryAccess())) {
            if (isEyeLayer(layer) && layer.isVariantInBounds(entity)) {
                GolemLayerListLayer.renderTexture(entity, getParentModel(), layer, poseStack,
                        bufferSource, packedLight, packedOverlay);
                renderedConfiguredEyes = true;
            }
        }

        // A handful of older models bake their eyes directly into a custom
        // entity texture. Preserve those exact pixels instead of substituting
        // the generic Bedrock/standard eye artwork.
        if (!renderedConfiguredEyes) {
            getEmbeddedEyeSpec(entity).ifPresent(spec -> renderEmbeddedEyes(
                    spec, poseStack, bufferSource, packedLight, packedOverlay));
        }

        getParentModel().resetColor();
        poseStack.popPose();
    }

    private static boolean isEyeLayer(final Layer layer) {
        final ResourcePair raw = layer.getRawTexture();
        if (!raw.flag()) {
            return false;
        }
        final ResourceLocation texture = raw.resource();
        return ExtraGolems.MODID.equals(texture.getNamespace())
                && ("eyes".equals(texture.getPath()) || texture.getPath().startsWith("eyes/"));
    }

    private Optional<EmbeddedEyeSpec> getEmbeddedEyeSpec(final T entity) {
        return entity.getGolemId().flatMap(id -> {
            if (!ExtraGolems.MODID.equals(id.getNamespace())) {
                return Optional.empty();
            }
            return switch (id.getPath()) {
                case "sea_lantern" -> Optional.of(new EmbeddedEyeSpec(entityTexture("sea_lantern.png"), false, false));
                case "glass" -> Optional.of(new EmbeddedEyeSpec(entityTexture("glass.png"), false, false));
                case "furnace" -> Optional.of(new EmbeddedEyeSpec(
                        entityTexture(entity.getVariant() == 0 ? "furnace/lit.png" : "furnace/unlit.png"), false, false));
                case "sculk", "sculk_catalyst" -> Optional.of(new EmbeddedEyeSpec(
                        entityTexture("layer/bioluminescence.png"), true, true));
                default -> Optional.empty();
            };
        });
    }

    private static ResourceLocation entityTexture(final String path) {
        return ResourceLocation.fromNamespaceAndPath(ExtraGolems.MODID, "textures/entity/golem/" + path);
    }

    private void renderEmbeddedEyes(final EmbeddedEyeSpec spec, final PoseStack poseStack,
                                    final MultiBufferSource bufferSource, final int packedLight,
                                    final int packedOverlay) {
        final Optional<ResourceLocation> oTexture = getOrCreateEmbeddedEyeTexture(spec.source());
        if (oTexture.isEmpty()) {
            return;
        }
        final RenderType renderType = spec.translucent()
                ? RenderType.entityTranslucent(oTexture.get())
                : RenderType.entityCutoutNoCull(oTexture.get());
        final VertexConsumer consumer = bufferSource.getBuffer(renderType);
        final int light = spec.emissive() ? LightTexture.FULL_BRIGHT : packedLight;
        getParentModel().resetColor();
        getParentModel().renderToBuffer(poseStack, consumer, light, packedOverlay, 0xFFFFFFFF);
    }

    private static Optional<ResourceLocation> getOrCreateEmbeddedEyeTexture(final ResourceLocation source) {
        final Minecraft minecraft = Minecraft.getInstance();
        final ResourceManager manager = minecraft.getResourceManager();

        // Resource reloads replace the manager instance. Clear our lookup so
        // the eye-only texture is rebuilt from the newly loaded resource pack.
        if (cachedResourceManager != manager) {
            EMBEDDED_EYE_CACHE.clear();
            cachedResourceManager = manager;
        }

        final ResourceLocation cached = EMBEDDED_EYE_CACHE.get(source);
        if (cached != null) {
            return Optional.of(cached);
        }

        final Optional<Resource> oSource = manager.getResource(source);
        final Optional<Resource> oMask = manager.getResource(EYE_MASK);
        if (oSource.isEmpty() || oMask.isEmpty()) {
            ExtraGolems.LOGGER.warn("Unable to build final eye layer from {}", source);
            return Optional.empty();
        }

        try (NativeImage sourceImage = NativeImage.read(oSource.get().open());
             NativeImage maskImage = NativeImage.read(oMask.get().open())) {
            final int width = sourceImage.getWidth();
            final int height = sourceImage.getHeight();
            final DynamicTexture eyeTexture = new DynamicTexture(width, height, true);
            final NativeImage output = eyeTexture.getPixels();

            for (int y = 0; y < height; ++y) {
                for (int x = 0; x < width; ++x) {
                    final int maskX = x * maskImage.getWidth() / width;
                    final int maskY = y * maskImage.getHeight() / height;
                    final int maskAlpha = maskImage.getLuminanceOrAlpha(maskX, maskY);
                    output.setPixelRGBA(x, y, maskAlpha == 0 ? 0 : sourceImage.getPixelRGBA(x, y));
                }
            }

            eyeTexture.upload();
            final ResourceLocation outputId = ResourceLocation.fromNamespaceAndPath(
                    ExtraGolems.MODID,
                    "dynamic/final_eyes/" + source.getNamespace() + "/" + source.getPath());
            minecraft.getTextureManager().register(outputId, eyeTexture);
            EMBEDDED_EYE_CACHE.put(source, outputId);
            return Optional.of(outputId);
        } catch (IOException exception) {
            ExtraGolems.LOGGER.error("Unable to build final eye layer from {}", source, exception);
            return Optional.empty();
        }
    }

    private record EmbeddedEyeSpec(ResourceLocation source, boolean emissive, boolean translucent) {}
}
