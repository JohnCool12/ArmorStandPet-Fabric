#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else 'work').resolve()
SRC = ROOT / 'src/main/java'

client = SRC / 'com/mcmoddev/golems/client/entity'
(client / 'layer').mkdir(parents=True, exist_ok=True)

(client / 'GolemRenderState.java').write_text(r'''package com.mcmoddev.golems.client.entity;

import com.mcmoddev.golems.data.model.Layer;
import net.minecraft.client.renderer.entity.state.IronGolemRenderState;

import java.util.List;

/** 26.1 render state carrying the data-driven Extra Golems material layers. */
public final class GolemRenderState extends IronGolemRenderState {
    public List<Layer> golemLayers = List.of();
    public int golemVariant;
    public int golemBiomeColor = 0xFFFFFF;
    public boolean hasGolemModel;
}
''')

(client / 'GolemDynamicTextures.java').write_text(r'''package com.mcmoddev.golems.client.entity;

import com.mcmoddev.golems.ExtraGolems;
import com.mcmoddev.golems.data.model.Layer;
import com.mojang.blaze3d.platform.NativeImage;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.texture.DynamicTexture;
import net.minecraft.resources.Identifier;
import net.minecraft.server.packs.resources.Resource;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/** Recreates the original Extra Golems dynamic material texture system on 26.1. */
public final class GolemDynamicTextures {
    private static final int TILES = 8;
    private static final Map<String, Identifier> CACHE = new HashMap<>();
    private GolemDynamicTextures() {}

    public static Identifier resolve(final Layer layer) {
        if (layer.getTexture().flag()) return layer.getTexture().resource();
        final Identifier source = layer.getTexture().resource();
        final Identifier template = layer.getTemplate();
        if (template == null) {
            ExtraGolems.LOGGER.error("Missing golem texture template for {}", source);
            return source;
        }
        return CACHE.computeIfAbsent(source + "|" + template, key -> build(source, template));
    }

    private static Identifier build(final Identifier source, final Identifier template) {
        final Identifier id = Identifier.fromNamespaceAndPath(ExtraGolems.MODID,
                "dynamic/" + Integer.toUnsignedString((source.toString() + "|" + template).hashCode(), 16));
        final Minecraft mc = Minecraft.getInstance();
        final Optional<Resource> sourceRes = mc.getResourceManager().getResource(source);
        final Optional<Resource> templateRes = mc.getResourceManager().getResource(template);
        if (sourceRes.isEmpty() || templateRes.isEmpty()) {
            ExtraGolems.LOGGER.error("Unable to locate golem material {} or template {}", source, template);
            return source;
        }
        try (NativeImage block = NativeImage.read(sourceRes.get().open());
             NativeImage mask = NativeImage.read(templateRes.get().open())) {
            final int blockWidth = block.getWidth();
            final int outputWidth = TILES * blockWidth;
            final int outputHeight = TILES * blockWidth;
            final int maskWidth = mask.getWidth();
            final int maskHeight = mask.getHeight();
            final NativeImage output = new NativeImage(outputWidth, outputHeight, true);
            for (int y = 0; y < outputHeight; ++y) {
                final int my = Math.min(maskHeight - 1, (int)((long)y * maskHeight / outputHeight));
                for (int x = 0; x < outputWidth; ++x) {
                    final int mx = Math.min(maskWidth - 1, (int)((long)x * maskWidth / outputWidth));
                    final int src = block.getPixel(x % blockWidth, y % block.getHeight());
                    final int sourceAlpha = (src >>> 24) & 0xFF;
                    final int maskAlpha = Byte.toUnsignedInt(mask.getLuminanceOrAlpha(mx, my));
                    final int alpha = sourceAlpha * maskAlpha / 255;
                    output.setPixel(x, y, (src & 0x00FFFFFF) | (alpha << 24));
                }
            }
            final DynamicTexture texture = new DynamicTexture(() -> "Extra Golems dynamic texture " + id, output);
            mc.getTextureManager().register(id, texture);
            texture.upload();
            return id;
        } catch (IOException | RuntimeException ex) {
            ExtraGolems.LOGGER.error("Failed building dynamic golem texture {} with template {}", source, template, ex);
            return source;
        }
    }

    public static void clear() { CACHE.clear(); }
}
''')

(client / 'layer/GolemLayerListLayer.java').write_text(r'''package com.mcmoddev.golems.client.entity.layer;

import com.mcmoddev.golems.client.entity.GolemDynamicTextures;
import com.mcmoddev.golems.client.entity.GolemRenderState;
import com.mcmoddev.golems.data.model.Layer;
import com.mcmoddev.golems.data.model.RenderTypes;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.model.animal.golem.IronGolemModel;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.entity.LivingEntityRenderer;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.resources.Identifier;

/** Native 26.1 render-state port of Extra Golems' material layer renderer. */
public final class GolemLayerListLayer extends RenderLayer<GolemRenderState, IronGolemModel> {
    private static final int FULL_BRIGHT = 0x00F000F0;

    public GolemLayerListLayer(RenderLayerParent<GolemRenderState, IronGolemModel> parent) { super(parent); }

    @Override
    public void submit(PoseStack poseStack, SubmitNodeCollector collector, int packedLight,
                       GolemRenderState state, float yRot, float xRot) {
        if (!state.hasGolemModel || state.golemLayers.isEmpty()) return;
        final int overlay = LivingEntityRenderer.getOverlayCoords(state, 0.0F);
        for (Layer layer : state.golemLayers) {
            if (!layer.isVariantInBounds(state.golemVariant)) continue;
            final Identifier texture = GolemDynamicTextures.resolve(layer);
            final int light = layer.isEmissive() ? FULL_BRIGHT : packedLight;
            final int rgb = layer.useBiomeColor() ? state.golemBiomeColor : layer.getPackedColor();
            final int tint = 0xFF000000 | (rgb & 0xFFFFFF);
            final net.minecraft.client.renderer.rendertype.RenderType type =
                    layer.getRenderType() == RenderTypes.TRANSLUCENT
                            ? net.minecraft.client.renderer.rendertype.RenderTypes.entityTranslucent(texture)
                            : net.minecraft.client.renderer.rendertype.RenderTypes.entityCutout(texture);
            collector.submitModel(getParentModel(), state, poseStack, type, light, overlay,
                    tint, null, state.outlineColor, null);
        }
    }
}
''')

(client / 'GolemRenderer.java').write_text(r'''package com.mcmoddev.golems.client.entity;

import com.mcmoddev.golems.data.GolemContainer;
import com.mcmoddev.golems.entity.GolemBase;
import com.mcmoddev.golems.client.entity.layer.GolemLayerListLayer;
import net.minecraft.client.model.animal.golem.IronGolemModel;
import net.minecraft.client.model.geom.ModelLayers;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.client.renderer.rendertype.RenderType;
import net.minecraft.resources.Identifier;
import org.jetbrains.annotations.Nullable;
import java.util.List;
import java.util.Optional;

/** 26.1 renderer restoring the original data-driven Extra Golems material layers. */
public final class GolemRenderer extends MobRenderer<GolemBase, GolemRenderState, IronGolemModel> {
    private static final Identifier FALLBACK = Identifier.withDefaultNamespace("textures/entity/iron_golem/iron_golem.png");
    public GolemRenderer(EntityRendererProvider.Context context) {
        super(context, new IronGolemModel(context.bakeLayer(ModelLayers.IRON_GOLEM)), 0.7F);
        this.addLayer(new GolemLayerListLayer(this));
    }
    @Override public GolemRenderState createRenderState() { return new GolemRenderState(); }
    @Override public void extractRenderState(GolemBase entity, GolemRenderState state, float partialTick) {
        super.extractRenderState(entity, state, partialTick);
        state.attackTicksRemaining = entity.getAttackAnimationTick() > 0 ? entity.getAttackAnimationTick() - partialTick : 0.0F;
        state.offerFlowerTick = entity.getOfferFlowerTick();
        state.crackiness = entity.getCrackiness();
        state.golemVariant = entity.getVariant();
        state.golemBiomeColor = entity.getBiomeColor();
        final Optional<GolemContainer> container = entity.getContainer();
        if (container.isPresent()) {
            state.hasGolemModel = true;
            state.golemLayers = List.copyOf(container.get().getModel().get(entity.level().registryAccess()));
        } else {
            state.hasGolemModel = false;
            state.golemLayers = List.of();
        }
    }
    @Override public Identifier getTextureLocation(GolemRenderState state) { return FALLBACK; }
    @Nullable @Override protected RenderType getRenderType(GolemRenderState state, boolean bodyVisible,
                                                            boolean forceTransparent, boolean appearGlowing) {
        return null;
    }
}
''')

events = SRC / 'com/mcmoddev/golems/EGEvents.java'
s = events.read_text()
old = '''\t\tpublic static void onServerStarted(final ServerStartedEvent event) {\n\t\t\tGolemContainer.populate(event.getServer().registryAccess());\n\t\t}\n'''
new = '''\t\tpublic static void onServerStarted(final ServerStartedEvent event) {\n\t\t\tGolemContainer.populate(event.getServer().registryAccess());\n\t\t\ttry {\n\t\t\t\tlong count = event.getServer().registryAccess().lookupOrThrow(EGRegistry.Keys.GOLEM).listElements().count();\n\t\t\t\tTagKey<net.minecraft.world.level.block.Block> diamondTag = TagKey.create(\n\t\t\t\t\t\tnet.minecraft.core.registries.BuiltInRegistries.BLOCK.key(),\n\t\t\t\t\t\tIdentifier.fromNamespaceAndPath("c", "storage_blocks/diamond"));\n\t\t\t\tboolean diamondTagged = Blocks.DIAMOND_BLOCK.builtInRegistryHolder().is(diamondTag);\n\t\t\t\tResourceKey<Golem> diamondMatch = ExtraGolems.getGolemId(event.getServer().overworld(),\n\t\t\t\t\t\tBlocks.DIAMOND_BLOCK, Blocks.DIAMOND_BLOCK, Blocks.DIAMOND_BLOCK, Blocks.DIAMOND_BLOCK);\n\t\t\t\tExtraGolems.LOGGER.info("[EGPORT] golem_count={} diamond_tag={} diamond_match={}",\n\t\t\t\t\t\tcount, diamondTagged, diamondMatch == null ? "null" : diamondMatch.identifier());\n\t\t\t} catch (Throwable t) {\n\t\t\t\tExtraGolems.LOGGER.error("[EGPORT] construction self-test failed", t);\n\t\t\t}\n\t\t}\n'''
if old not in s: raise SystemExit('Unexpected onServerStarted block for runtime diagnostic')
events.write_text(s.replace(old, new))
print('Applied native 26.1 data-driven renderer + runtime construction diagnostic pass 11')
