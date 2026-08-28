#!/usr/bin/env python3
from pathlib import Path
import re, sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else 'work').resolve()
CLIENT = ROOT / 'src/main/java/com/mcmoddev/golems/client'
ENTITY = CLIENT / 'entity'
LAYER = ENTITY / 'layer'

# Legacy 1.21 RenderStateShard/RenderType implementations cannot exist in 26.1.
for obsolete in [ENTITY/'DynamicTextureState.java', ENTITY/'GolemRenderType.java']:
    if obsolete.exists(): obsolete.unlink()

# Preserve the upstream 128x128 Extra Golems mesh, but adapt the model class itself
# to Mojang's 26.1 render-state model API. The body-layer definition is intentionally
# left byte-for-byte semantically equivalent to upstream.
model = ENTITY / 'GolemModel.java'
s = model.read_text()
s = s.replace('import com.mcmoddev.golems.entity.GolemBase;\n', '')
s = s.replace('import com.mojang.blaze3d.vertex.VertexConsumer;\n', '')
s = s.replace('import net.minecraft.ChatFormatting;\n', '')
s = s.replace('import net.minecraft.client.renderer.rendertype.RenderType;\n', '')
s = s.replace('import net.minecraft.client.renderer.entity.LivingEntityRenderer;\n', '')
s = s.replace('public class GolemModel<T extends GolemBase> extends IronGolemModel<T> implements ArmedModel {',
              'public class GolemModel extends IronGolemModel implements ArmedModel<GolemRenderState> {')
s = re.sub(r'\n\s*private float red = 1\.0F;\n\s*private float green = 1\.0F;\n\s*private float blue = 1\.0F;\n', '\n', s)
# Remove the old direct-buffer rendering/color API and old entity-based setupAnim.
s = re.sub(r'\n\s*//// RENDER ////.*?\n\s*//// ANIMATIONS ////\n', '\n\n\t//// ANIMATIONS ////\n', s, flags=re.S)
s = re.sub(r'\n\s*@Override\s+public void setupAnim\(T entity, float limbSwing, float limbSwingAmount, float partialTicks, float netHeadYaw, float headPitch\) \{.*?\n\s*\}', '', s, flags=re.S)
s = re.sub(r'public void setupKittyAnim\(T entity, float limbSwing, float limbSwingAmount, float partialTicks, float netHeadYaw, float headPitch\)',
           'public void setupKittyAnim(GolemRenderState state)', s)
s = s.replace('float idleSwing = Mth.cos((entity.tickCount + entity.getId() + partialTicks) * 0.058F);',
              'float idleSwing = Mth.cos(state.golemAnimationPhase * 0.058F);')
s = s.replace('float tailSwing = Mth.cos(limbSwing) * limbSwingAmount;',
              'float tailSwing = Mth.cos(state.walkAnimationPos) * state.walkAnimationSpeed;')
# Remove obsolete per-model tint state; tint is now supplied to SubmitNodeCollector.
s = re.sub(r'\n\s*//// COLOR ////.*?\n\s*//// ARMED MODEL ////\n', '\n\n\t//// ARMED MODEL ////\n', s, flags=re.S)
s = s.replace('public void translateToHand(HumanoidArm hand, PoseStack matrixStack) {',
              'public void translateToHand(GolemRenderState state, HumanoidArm hand, PoseStack matrixStack) {')
model.write_text(s)

# Complete render state: all entity-dependent decisions are extracted before deferred
# feature submission, so layers never reach back into a live entity during rendering.
(ENTITY/'GolemRenderState.java').write_text(r'''package com.mcmoddev.golems.client.entity;

import com.mcmoddev.golems.data.model.Layer;
import net.minecraft.client.renderer.entity.state.IronGolemRenderState;
import net.minecraft.resources.Identifier;
import net.minecraft.world.item.ItemStack;
import org.jetbrains.annotations.Nullable;
import java.util.List;

public final class GolemRenderState extends IronGolemRenderState {
    public boolean hasGolemModel;
    public List<Layer> golemLayers = List.of();
    public int golemVariant;
    public int golemBiomeColor = 0xFFFFFF;
    public boolean prideLayer;
    public boolean kittyLayer;
    public float golemAnimationPhase;
    public @Nullable Identifier overrideTexture;
    public ItemStack bannerStack = ItemStack.EMPTY;
}
''')

# 26.1 renderer using the real upstream Extra Golems mesh and deferred render states.
(ENTITY/'GolemRenderer.java').write_text(r'''package com.mcmoddev.golems.client.entity;

import com.mcmoddev.golems.ExtraGolems;
import com.mcmoddev.golems.data.GolemContainer;
import com.mcmoddev.golems.entity.GolemBase;
import com.mcmoddev.golems.client.entity.layer.*;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import net.minecraft.ChatFormatting;
import net.minecraft.client.model.geom.ModelLayerLocation;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.client.renderer.rendertype.RenderType;
import net.minecraft.resources.Identifier;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.EquipmentSlot;
import org.jetbrains.annotations.Nullable;
import java.util.List;
import java.util.Locale;
import java.util.Optional;

/** Full 26.1 render-state port retaining Extra Golems' custom 128x128 model. */
public final class GolemRenderer extends MobRenderer<GolemBase, GolemRenderState, GolemModel> {
    public static final ModelLayerLocation GOLEM_MODEL_RESOURCE = new ModelLayerLocation(
            Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "golem"), "main");
    private static final Identifier FALLBACK = Identifier.withDefaultNamespace("textures/entity/iron_golem/iron_golem.png");
    private static final Identifier BONE_SKELETON = id("textures/entity/golem/bone_skeleton.png");
    private static final Identifier GANON = id("textures/entity/golem/ganon.png");
    private static final Identifier COOKIE = id("textures/entity/golem/cookie.png");
    private static final Identifier YETI = id("textures/entity/golem/yeti.png");
    private static final Identifier HARAMBE = id("textures/entity/golem/harambe.png");

    private static Identifier id(String path) { return Identifier.fromNamespaceAndPath(ExtraGolems.MODID, path); }

    public GolemRenderer(EntityRendererProvider.Context context) {
        super(context, new GolemModel(context.bakeLayer(GOLEM_MODEL_RESOURCE)), 0.5F);
        this.addLayer(new GolemLayerListLayer(this));
        this.addLayer(new GolemTextureOverrideLayer(this));
        this.addLayer(new GolemCrackinessLayer(this));
        this.addLayer(new GolemKittyLayer(this));
        // Flower/banner are restored in the next feature-state pass after the core
        // model/layer API has been validated by the compiler.
    }

    @Override public GolemRenderState createRenderState() { return new GolemRenderState(); }

    @Override
    public void extractRenderState(GolemBase entity, GolemRenderState state, float partialTick) {
        super.extractRenderState(entity, state, partialTick);
        state.attackTicksRemaining = entity.getAttackAnimationTick() > 0 ? entity.getAttackAnimationTick() - partialTick : 0.0F;
        state.offerFlowerTick = entity.getOfferFlowerTick();
        state.crackiness = entity.getCrackiness();
        state.golemVariant = entity.getVariant();
        state.golemBiomeColor = entity.getBiomeColor();
        state.golemAnimationPhase = entity.tickCount + entity.getId() + partialTick;
        final Optional<GolemContainer> container = entity.getContainer();
        if (container.isPresent()) {
            state.hasGolemModel = true;
            state.golemLayers = List.copyOf(container.get().getModel().get(entity.level().registryAccess()));
        } else {
            state.hasGolemModel = false;
            state.golemLayers = List.of();
        }
        final String name = ChatFormatting.stripFormatting(entity.getName().getString()).toLowerCase(Locale.ENGLISH);
        state.prideLayer = ExtraGolems.CONFIG.pride() || name.startsWith("lgbt");
        state.kittyLayer = entity.hasCustomName() && "kitty".equalsIgnoreCase(name);
        state.overrideTexture = null;
        final long time = entity.level().getDayTime() % 24000L;
        if (ExtraGolems.CONFIG.halloween() && time > 13000L && time < 23000L) state.overrideTexture = BONE_SKELETON;
        else if ("ganon".equals(name) || "ganondorf".equals(name)) state.overrideTexture = GANON;
        else if ("cookie".equals(name)) state.overrideTexture = COOKIE;
        else if ("yeti".equals(name)) state.overrideTexture = YETI;
        else if ("harambe".equals(name)) state.overrideTexture = HARAMBE;
        state.bannerStack = entity.getItemBySlot(EquipmentSlot.CHEST).copy();
    }

    @Override public Identifier getTextureLocation(GolemRenderState state) { return FALLBACK; }

    @Nullable @Override
    protected RenderType getRenderType(GolemRenderState state, boolean bodyVisible, boolean forceTransparent, boolean appearGlowing) {
        // Material/override layers own the visible model. This prevents the fallback
        // vanilla iron texture from ever leaking through beneath Extra Golems layers.
        return null;
    }

    @Override
    protected void setupRotations(GolemRenderState state, PoseStack poseStack, float bodyRot, float entityScale) {
        super.setupRotations(state, poseStack, bodyRot, entityScale);
        if (ExtraGolems.CONFIG.aprilFools()) {
            poseStack.translate(0.0D, state.boundingBoxHeight + 0.1D, 0.0D);
            poseStack.mulPose(Axis.ZP.rotationDegrees(180.0F));
        }
        if (state.walkAnimationSpeed >= 0.01F) {
            float f = 13.0F;
            float f1 = state.walkAnimationPos + 6.0F;
            float f2 = (Mth.abs(f1 % f - f * 0.5F) - f * 0.25F) / (f * 0.25F);
            poseStack.mulPose(Axis.ZP.rotationDegrees(6.5F * f2 * state.walkAnimationSpeed));
        }
    }

    @Override
    protected void scale(GolemRenderState state, PoseStack poseStack) {
        if (state.isBaby) poseStack.scale(0.5F, 0.5F, 0.5F);
        super.scale(state, poseStack);
    }
}
''')

# Material layers + pride layer. Dynamic block textures are resolved by the already
# compiling GolemDynamicTextures helper introduced in pass 11.
(LAYER/'GolemLayerListLayer.java').write_text(r'''package com.mcmoddev.golems.client.entity.layer;

import com.mcmoddev.golems.client.entity.GolemDynamicTextures;
import com.mcmoddev.golems.client.entity.GolemModel;
import com.mcmoddev.golems.client.entity.GolemRenderState;
import com.mcmoddev.golems.data.model.Layer;
import com.mcmoddev.golems.data.model.RenderTypes;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.entity.LivingEntityRenderer;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.resources.Identifier;

public final class GolemLayerListLayer extends RenderLayer<GolemRenderState, GolemModel> {
    private static final int FULL_BRIGHT = 0x00F000F0;
    public GolemLayerListLayer(RenderLayerParent<GolemRenderState, GolemModel> parent) { super(parent); }

    @Override
    public void submit(PoseStack poseStack, SubmitNodeCollector collector, int packedLight,
                       GolemRenderState state, float yRot, float xRot) {
        if (!state.hasGolemModel || state.isInvisibleToPlayer || state.overrideTexture != null) return;
        final int overlay = LivingEntityRenderer.getOverlayCoords(state, 0.0F);
        for (Layer layer : state.golemLayers) submitLayer(layer, poseStack, collector, packedLight, overlay, state);
        if (state.prideLayer) submitLayer(Layer.RAINBOW, poseStack, collector, packedLight, overlay, state);
    }

    private void submitLayer(Layer layer, PoseStack poseStack, SubmitNodeCollector collector, int packedLight,
                             int overlay, GolemRenderState state) {
        if (!layer.isVariantInBounds(state.golemVariant)) return;
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
''')

(LAYER/'GolemTextureOverrideLayer.java').write_text(r'''package com.mcmoddev.golems.client.entity.layer;

import com.mcmoddev.golems.client.entity.GolemModel;
import com.mcmoddev.golems.client.entity.GolemRenderState;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.client.renderer.rendertype.RenderTypes;

public final class GolemTextureOverrideLayer extends RenderLayer<GolemRenderState, GolemModel> {
    public GolemTextureOverrideLayer(RenderLayerParent<GolemRenderState, GolemModel> parent) { super(parent); }
    @Override
    public void submit(PoseStack poseStack, SubmitNodeCollector collector, int packedLight,
                       GolemRenderState state, float yRot, float xRot) {
        if (state.overrideTexture == null || state.isInvisibleToPlayer) return;
        renderColoredCutoutModel(getParentModel(), state.overrideTexture, poseStack, collector,
                packedLight, state, 0xFFFFFFFF, 0);
    }
}
''')

(LAYER/'GolemCrackinessLayer.java').write_text(r'''package com.mcmoddev.golems.client.entity.layer;

import com.mcmoddev.golems.client.entity.GolemModel;
import com.mcmoddev.golems.client.entity.GolemRenderState;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.entity.LivingEntityRenderer;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.client.renderer.rendertype.RenderTypes;
import net.minecraft.resources.Identifier;

public final class GolemCrackinessLayer extends RenderLayer<GolemRenderState, GolemModel> {
    private static final Identifier LOW = Identifier.withDefaultNamespace("textures/entity/iron_golem/iron_golem_crackiness_low.png");
    private static final Identifier MEDIUM = Identifier.withDefaultNamespace("textures/entity/iron_golem/iron_golem_crackiness_medium.png");
    private static final Identifier HIGH = Identifier.withDefaultNamespace("textures/entity/iron_golem/iron_golem_crackiness_high.png");
    public GolemCrackinessLayer(RenderLayerParent<GolemRenderState, GolemModel> parent) { super(parent); }
    @Override
    public void submit(PoseStack poseStack, SubmitNodeCollector collector, int packedLight,
                       GolemRenderState state, float yRot, float xRot) {
        if (state.isInvisible) return;
        Identifier texture = switch (state.crackiness) {
            case HIGH -> HIGH;
            case MEDIUM -> MEDIUM;
            case LOW -> LOW;
            default -> null;
        };
        if (texture == null) return;
        collector.submitModel(getParentModel(), state, poseStack, RenderTypes.entityTranslucent(texture),
                packedLight, LivingEntityRenderer.getOverlayCoords(state, 0.0F), 0x80FFFFFF,
                null, state.outlineColor, null);
    }
}
''')

(LAYER/'GolemKittyLayer.java').write_text(r'''package com.mcmoddev.golems.client.entity.layer;

import com.mcmoddev.golems.ExtraGolems;
import com.mcmoddev.golems.client.entity.GolemModel;
import com.mcmoddev.golems.client.entity.GolemRenderState;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.entity.LivingEntityRenderer;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.client.renderer.rendertype.RenderTypes;
import net.minecraft.resources.Identifier;

public final class GolemKittyLayer extends RenderLayer<GolemRenderState, GolemModel> {
    private static final Identifier TEXTURE = Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "textures/entity/golem/layer/kitty_layer.png");
    public GolemKittyLayer(RenderLayerParent<GolemRenderState, GolemModel> parent) { super(parent); }
    @Override
    public void submit(PoseStack poseStack, SubmitNodeCollector collector, int packedLight,
                       GolemRenderState state, float yRot, float xRot) {
        if (!state.kittyLayer || state.isInvisible) return;
        getParentModel().setupKittyAnim(state);
        collector.submitModelPart(getParentModel().getKitty(), poseStack, RenderTypes.entityCutoutNoCull(TEXTURE),
                packedLight, LivingEntityRenderer.getOverlayCoords(state, 0.0F), null,
                0xFFFFFFFF, null);
    }
}
''')

# Remove legacy flower/banner source for this compile-isolation pass. They are restored
# as native 26.1 feature submissions after the custom model/material core is green.
for deferred in [LAYER/'GolemFlowerLayer.java', LAYER/'GolemBannerLayer.java']:
    if deferred.exists(): deferred.unlink()

print('Applied full custom-model 26.1 render-state core pass 16')
