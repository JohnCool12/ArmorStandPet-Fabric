from pathlib import Path
import re

root = Path('project/src/main/java/com/mcmoddev/golems/client')

def write(rel, text):
    p=root/rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def edit(rel, fn):
    p=root/rel; s=p.read_text(); p.write_text(fn(s))

# Dedicated 26.1 extraction state. No world/entity references are retained by the render pipeline.
write('entity/GolemRenderState.java', r'''package com.mcmoddev.golems.client.entity;

import com.mcmoddev.golems.data.model.Layer;
import net.minecraft.client.renderer.entity.state.IronGolemRenderState;
import net.minecraft.client.renderer.item.ItemStackRenderState;
import net.minecraft.resources.Identifier;

import java.util.List;

public class GolemRenderState extends IronGolemRenderState {
    public boolean valid;
    public List<Layer> layers = List.of();
    public int variant;
    public int biomeColor = 0xFFFFFF;
    public boolean prideLayer;
    public Identifier overrideTexture;
    public boolean kittyVisible;
    public int entityId;
    public final ItemStackRenderState bannerItem = new ItemStackRenderState();
}
''')

# Adapt the existing custom mesh to the render-state model without altering its geometry/UVs.
def patch_model(s):
    s=s.replace('import com.mcmoddev.golems.entity.GolemBase;\n','')
    s=s.replace('import com.mojang.blaze3d.vertex.VertexConsumer;\n','')
    s=s.replace('import net.minecraft.ChatFormatting;\n','')
    s=s.replace('import net.minecraft.client.model.IronGolemModel;','import net.minecraft.client.model.animal.golem.IronGolemModel;')
    s=s.replace('import net.minecraft.client.renderer.RenderType;\n','')
    s=s.replace('import net.minecraft.client.renderer.entity.LivingEntityRenderer;\n','')
    s=s.replace('public class GolemModel<T extends GolemBase> extends IronGolemModel<T> implements ArmedModel {','public class GolemModel extends IronGolemModel implements ArmedModel<GolemRenderState> {')
    s=re.sub(r'\n\tprivate float red = 1\.0F;\n\tprivate float green = 1\.0F;\n\tprivate float blue = 1\.0F;\n','\n',s)
    # Replace legacy direct-render/color section; geometry and kitty parts remain unchanged.
    start=s.index('\n\t//// RENDER ////')
    end=s.index('\n\t//// ARMED MODEL ////')
    replacement=r'''
	//// ANIMATIONS ////

	public void setupKittyAnim(GolemRenderState state) {
		this.ears.copyFrom(this.root().getChild("head"));
		this.tail.y = 2.0F;
		this.tail.z = 4.0F;
		float idleSwing = Mth.cos((state.ageInTicks + state.entityId) * 0.058F);
		float tailSwing = Mth.cos(state.walkAnimationPos) * state.walkAnimationSpeed;
		tail.xRot = -2.4435F + 0.38F * tailSwing;
		tail1.xRot = 0.2618F + 0.48F * tailSwing;
		tail.zRot = 0.06F * idleSwing;
		tail1.zRot = -0.05F * idleSwing;
	}
'''
    s=s[:start]+replacement+s[end:]
    s=s.replace('public void translateToHand(HumanoidArm hand, PoseStack matrixStack) {','public void translateToHand(GolemRenderState state, HumanoidArm hand, PoseStack matrixStack) {')
    return s
edit('entity/GolemModel.java', patch_model)

write('entity/DynamicTextureState.java', r'''package com.mcmoddev.golems.client.entity;

import com.mcmoddev.golems.ExtraGolems;
import com.mojang.blaze3d.platform.NativeImage;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.texture.DynamicTexture;
import net.minecraft.client.renderer.texture.TextureManager;
import net.minecraft.resources.Identifier;
import net.minecraft.server.packs.resources.Resource;

import java.io.IOException;
import java.util.Optional;

/** Builds the legacy block-texture-on-golem-template image and registers it as a normal 26.1 texture. */
public class DynamicTextureState {
    protected static final int TILES = 8;
    private final Identifier location;
    private final Identifier sourceImage;
    private final Identifier templateImage;
    private final DynamicTexture dynamicTexture;

    public DynamicTextureState(Identifier id, Identifier blockName, Identifier templateName) {
        this.location = id;
        this.sourceImage = blockName;
        this.templateImage = templateName;
        DynamicTexture texture;
        Optional<Resource> blockRes = Minecraft.getInstance().getResourceManager().getResource(blockName);
        Optional<Resource> templateRes = Minecraft.getInstance().getResourceManager().getResource(templateName);
        if (blockRes.isPresent() && templateRes.isPresent()) {
            try (NativeImage block = NativeImage.read(blockRes.get().open()); NativeImage template = NativeImage.read(templateRes.get().open())) {
                int blockWidth = block.getWidth();
                int outputWidth = TILES * blockWidth;
                int outputHeight = TILES * blockWidth;
                int templateWidth = template.getWidth();
                int templateHeight = template.getHeight();
                float scale = (float) outputWidth / (float) templateWidth;
                texture = new DynamicTexture(() -> "Extra Golems dynamic texture " + id, outputWidth, outputHeight, true);
                NativeImage output = texture.getPixels();
                for (int y = 0; y < outputHeight; y++) {
                    for (int x = 0; x < outputWidth; x++) {
                        int mask = template.getLuminanceOrAlpha((int)(x / scale) % templateWidth, (int)(y / scale) % templateHeight);
                        output.setPixel(x, y, block.getPixel(x % blockWidth, y % blockWidth) & mask);
                    }
                }
            } catch (IOException | RuntimeException e) {
                ExtraGolems.LOGGER.error("Error opening dynamic golem texture {} with template {}", blockName, templateName, e);
                texture = fallback(id);
            }
        } else {
            ExtraGolems.LOGGER.error("Error locating dynamic golem texture {} with template {}", blockName, templateName);
            texture = fallback(id);
        }
        this.dynamicTexture = texture;
        this.dynamicTexture.upload();
        TextureManager manager = Minecraft.getInstance().getTextureManager();
        manager.register(location, dynamicTexture);
    }

    private static DynamicTexture fallback(Identifier id) {
        DynamicTexture texture = new DynamicTexture(() -> "Extra Golems fallback texture " + id, 16 * TILES, 16 * TILES, true);
        texture.getPixels().fillRect(0, 0, 16 * TILES, 16 * TILES, 0xFFFFFFFF);
        return texture;
    }

    public Identifier getLocation() { return location; }
    public Identifier getSourceImage() { return sourceImage; }
    public Identifier getTemplateImage() { return templateImage; }
    public DynamicTexture getTexture() { return dynamicTexture; }
}
''')

write('entity/GolemRenderType.java', r'''package com.mcmoddev.golems.client.entity;

import net.minecraft.client.renderer.rendertype.RenderType;
import net.minecraft.client.renderer.rendertype.RenderTypes;
import net.minecraft.resources.Identifier;

import java.util.HashMap;
import java.util.Map;

/** 26.1 render-type bridge. Dynamic images are registered textures, so native entity pipelines can be reused. */
public final class GolemRenderType {
    private static final Map<Identifier, DynamicTextureState> DYNAMIC_TEXTURES = new HashMap<>();
    private GolemRenderType() {}

    public static void reloadDynamicTextureMap() {
        Map<Identifier, DynamicTextureState> old = new HashMap<>(DYNAMIC_TEXTURES);
        DYNAMIC_TEXTURES.clear();
        old.forEach((id, state) -> DYNAMIC_TEXTURES.put(id, new DynamicTextureState(id, state.getSourceImage(), state.getTemplateImage())));
    }

    private static Identifier texture(Identifier source, Identifier template, boolean dynamic) {
        if (!dynamic || template == null) return source;
        Identifier id = Identifier.fromNamespaceAndPath(source.getNamespace(), "dynamic/" + template.getPath() + "/" + source.getPath());
        DYNAMIC_TEXTURES.computeIfAbsent(id, key -> new DynamicTextureState(key, source, template));
        return id;
    }

    public static RenderType getGolemCutout(Identifier source, Identifier template, boolean dynamic) {
        return RenderTypes.entityCutout(texture(source, template, dynamic));
    }
    public static RenderType getGolemTranslucent(Identifier source, Identifier template, boolean dynamic) {
        return RenderTypes.entityTranslucent(texture(source, template, dynamic));
    }
    public static RenderType getGolemOutline(Identifier source, Identifier template, boolean dynamic) {
        return RenderTypes.outline(texture(source, template, dynamic));
    }
}
''')

write('entity/GolemRenderer.java', r'''package com.mcmoddev.golems.client.entity;

import com.mcmoddev.golems.ExtraGolems;
import com.mcmoddev.golems.client.entity.layer.*;
import com.mcmoddev.golems.data.GolemContainer;
import com.mcmoddev.golems.entity.GolemBase;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import net.minecraft.ChatFormatting;
import net.minecraft.client.model.geom.ModelLayerLocation;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.block.BlockModelResolver;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.IronGolemRenderer;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.client.renderer.rendertype.RenderType;
import net.minecraft.client.renderer.state.level.CameraRenderState;
import net.minecraft.resources.Identifier;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.Crackiness;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Blocks;

import java.util.List;
import java.util.Locale;
import java.util.Optional;

public class GolemRenderer extends MobRenderer<GolemBase, GolemRenderState, GolemModel> {
    public static final ModelLayerLocation GOLEM_MODEL_RESOURCE = new ModelLayerLocation(Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "golem"), "main");
    private static final Identifier GOLEM_LOCATION = Identifier.withDefaultNamespace("textures/entity/iron_golem/iron_golem.png");
    private final BlockModelResolver blockModelResolver;

    public GolemRenderer(EntityRendererProvider.Context context) {
        super(context, new GolemModel(context.bakeLayer(GOLEM_MODEL_RESOURCE)), 0.5F);
        this.blockModelResolver = context.getBlockModelResolver();
        this.addLayer(new GolemLayerListLayer(this));
        this.addLayer(new GolemTextureOverrideLayer(this));
        this.addLayer(new GolemCrackinessLayer(this));
        this.addLayer(new GolemFlowerLayer(this));
        this.addLayer(new GolemKittyLayer(this));
        this.addLayer(new GolemBannerLayer(this));
    }

    @Override public GolemRenderState createRenderState() { return new GolemRenderState(); }

    @Override
    public void extractRenderState(GolemBase entity, GolemRenderState state, float partialTick) {
        super.extractRenderState(entity, state, partialTick);
        Optional<GolemContainer> container = entity.getContainer();
        state.valid = container.isPresent();
        state.attackTicksRemaining = entity.getAttackAnimationTick() > 0 ? entity.getAttackAnimationTick() - partialTick : 0.0F;
        state.offerFlowerTick = entity.getOfferFlowerTick();
        if (state.offerFlowerTick > 0) {
            blockModelResolver.update(state.flowerBlock, Blocks.POPPY.defaultBlockState(), IronGolemRenderer.BLOCK_DISPLAY_CONTEXT);
        } else {
            state.flowerBlock.clear();
        }
        state.crackiness = entity.getCrackiness();
        state.variant = entity.getVariant();
        state.biomeColor = entity.getBiomeColor();
        state.entityId = entity.getId();
        state.layers = container.map(c -> List.copyOf(c.getModel().get(entity.level().registryAccess()))).orElseGet(List::of);
        String rawName = ChatFormatting.stripFormatting(entity.getName().getString());
        String name = rawName == null ? "" : rawName;
        state.prideLayer = ExtraGolems.CONFIG.pride() || name.toLowerCase(Locale.ENGLISH).startsWith("lgbt");
        state.kittyVisible = entity.hasCustomName() && "kitty".equalsIgnoreCase(name);
        state.overrideTexture = GolemTextureOverrideLayer.getOverrideTexture(entity).orElse(null);
        state.bannerItem.clear();
        ItemStack banner = entity.getItemBySlot(EquipmentSlot.CHEST);
        if (banner.is(ItemTags.BANNERS)) {
            this.itemModelResolver.updateForLiving(state.bannerItem, banner, ItemDisplayContext.FIRST_PERSON_RIGHT_HAND, entity);
        }
    }

    @Override
    public void submit(GolemRenderState state, PoseStack poseStack, SubmitNodeCollector collector, CameraRenderState cameraState) {
        if (!state.valid) return;
        super.submit(state, poseStack, collector, cameraState);
    }

    @Override
    protected void setupRotations(GolemRenderState state, PoseStack poseStack, float bodyRot, float scale) {
        super.setupRotations(state, poseStack, bodyRot, scale);
        if (ExtraGolems.CONFIG.aprilFirst()) {
            poseStack.translate(0.0F, state.boundingBoxHeight + 0.1F, 0.0F);
            poseStack.mulPose(Axis.ZP.rotationDegrees(180.0F));
        }
        if (state.walkAnimationSpeed >= 0.01F) {
            float maxAngle = 13.0F * state.scale;
            float walkAnimation = state.walkAnimationPos + 6.0F;
            float walkAngle = (Math.abs(walkAnimation % maxAngle - (maxAngle / 2.0F)) - 3.25F) / 3.25F;
            poseStack.mulPose(Axis.ZP.rotationDegrees((maxAngle / 2.0F) * walkAngle));
        }
    }

    @Override public Identifier getTextureLocation(GolemRenderState state) { return GOLEM_LOCATION; }

    @Override
    protected RenderType getRenderType(GolemRenderState state, boolean bodyVisible, boolean translucent, boolean glowing) {
        // The full body is data-driven and rendered by GolemLayerListLayer / texture override layer.
        return null;
    }
}
''')

write('entity/layer/GolemLayerListLayer.java', r'''package com.mcmoddev.golems.client.entity.layer;

import com.mcmoddev.golems.client.entity.GolemModel;
import com.mcmoddev.golems.client.entity.GolemRenderState;
import com.mcmoddev.golems.client.entity.GolemRenderType;
import com.mcmoddev.golems.data.ResourcePair;
import com.mcmoddev.golems.data.model.Layer;
import com.mcmoddev.golems.data.model.RenderTypes;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.entity.LivingEntityRenderer;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.client.renderer.rendertype.RenderType;
import net.minecraft.resources.Identifier;

public class GolemLayerListLayer extends RenderLayer<GolemRenderState, GolemModel> {
    public GolemLayerListLayer(RenderLayerParent<GolemRenderState, GolemModel> parent) { super(parent); }

    @Override
    public void submit(PoseStack poseStack, SubmitNodeCollector collector, int packedLight, GolemRenderState state, float yRot, float xRot) {
        if (!state.valid || state.overrideTexture != null || state.isInvisibleToPlayer || state.layers.isEmpty()) return;
        int overlay = LivingEntityRenderer.getOverlayCoords(state, 0.0F);
        for (Layer layer : state.layers) {
            if (layer.isVariantInBounds(state.variant)) renderTexture(state, getParentModel(), layer, poseStack, collector, packedLight, overlay);
        }
        if (state.prideLayer) renderTexture(state, getParentModel(), Layer.RAINBOW, poseStack, collector, packedLight, overlay);
    }

    private static void renderTexture(GolemRenderState state, GolemModel model, Layer layer, PoseStack poseStack, SubmitNodeCollector collector, int packedLightIn, int overlay) {
        int light = layer.isEmissive() ? 0x00F000F0 : packedLightIn;
        int rgb = layer.useBiomeColor() ? state.biomeColor : layer.getPackedColor();
        int alpha = layer.getRenderType() == RenderTypes.TRANSLUCENT ? 0x80 : 0xFF;
        int color = (alpha << 24) | (rgb & 0x00FFFFFF);
        RenderType renderType = getRenderType(layer.getRenderType(), layer.getTexture(), layer.getTemplate());
        collector.order(0).submitModel(model, state, poseStack, renderType, light, overlay, color, null, state.outlineColor, null);
    }

    private static RenderType getRenderType(RenderTypes type, ResourcePair texture, Identifier template) {
        return type == RenderTypes.TRANSLUCENT
                ? GolemRenderType.getGolemTranslucent(texture.resource(), template, !texture.flag())
                : GolemRenderType.getGolemCutout(texture.resource(), template, !texture.flag());
    }
}
''')

write('entity/layer/GolemTextureOverrideLayer.java', r'''package com.mcmoddev.golems.client.entity.layer;

import com.mcmoddev.golems.ExtraGolems;
import com.mcmoddev.golems.client.entity.GolemModel;
import com.mcmoddev.golems.client.entity.GolemRenderState;
import com.mcmoddev.golems.entity.GolemBase;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.ChatFormatting;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.world.clock.WorldClocks;

import java.util.Locale;
import java.util.Optional;

public class GolemTextureOverrideLayer extends RenderLayer<GolemRenderState, GolemModel> {
    private static final Identifier BONE_SKELETON = Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "textures/entity/golem/bone_skeleton.png");
    private static final Identifier GANON = Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "textures/entity/golem/ganon.png");
    private static final Identifier COOKIE = Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "textures/entity/golem/cookie.png");
    private static final Identifier YETI = Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "textures/entity/golem/yeti.png");
    private static final Identifier HARAMBE = Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "textures/entity/golem/harambe.png");

    public GolemTextureOverrideLayer(RenderLayerParent<GolemRenderState, GolemModel> parent) { super(parent); }

    @Override
    public void submit(PoseStack poseStack, SubmitNodeCollector collector, int packedLight, GolemRenderState state, float yRot, float xRot) {
        if (!state.valid || state.overrideTexture == null || state.isInvisibleToPlayer) return;
        renderColoredCutoutModel(getParentModel(), state.overrideTexture, poseStack, collector, packedLight, state, 0xFFFFFFFF, 0);
    }

    public static Optional<Identifier> getOverrideTexture(GolemBase entity) {
        if (ExtraGolems.CONFIG.halloween() && isNightTime(entity)) return Optional.of(BONE_SKELETON);
        String raw = ChatFormatting.stripFormatting(entity.getName().getString());
        String name = raw == null ? "" : raw.toLowerCase(Locale.ENGLISH);
        if ("ganon".equals(name) || "ganondorf".equals(name)) return Optional.of(GANON);
        if ("cookie".equals(name)) return Optional.of(COOKIE);
        if ("yeti".equals(name)) return Optional.of(YETI);
        if ("harambe".equals(name)) return Optional.of(HARAMBE);
        return Optional.empty();
    }

    private static boolean isNightTime(GolemBase golem) {
        try {
            var clocks = golem.level().registryAccess().lookupOrThrow(Registries.WORLD_CLOCK);
            var overworld = clocks.getOrThrow(WorldClocks.OVERWORLD);
            long time = golem.level().clockManager().getTotalTicks(overworld) % 24000L;
            return time > 13000L && time < 23000L;
        } catch (RuntimeException ex) {
            long time = golem.level().getLevelData().getGameTime() % 24000L;
            return time > 13000L && time < 23000L;
        }
    }
}
''')

write('entity/layer/GolemCrackinessLayer.java', r'''package com.mcmoddev.golems.client.entity.layer;

import com.mcmoddev.golems.client.entity.GolemModel;
import com.mcmoddev.golems.client.entity.GolemRenderState;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.entity.LivingEntityRenderer;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.client.renderer.rendertype.RenderTypes;
import net.minecraft.resources.Identifier;
import net.minecraft.world.entity.Crackiness;

public class GolemCrackinessLayer extends RenderLayer<GolemRenderState, GolemModel> {
    private static final Identifier LOW = Identifier.withDefaultNamespace("textures/entity/iron_golem/iron_golem_crackiness_low.png");
    private static final Identifier MEDIUM = Identifier.withDefaultNamespace("textures/entity/iron_golem/iron_golem_crackiness_medium.png");
    private static final Identifier HIGH = Identifier.withDefaultNamespace("textures/entity/iron_golem/iron_golem_crackiness_high.png");

    public GolemCrackinessLayer(RenderLayerParent<GolemRenderState, GolemModel> parent) { super(parent); }

    @Override
    public void submit(PoseStack poseStack, SubmitNodeCollector collector, int packedLight, GolemRenderState state, float yRot, float xRot) {
        if (state.isInvisible || state.crackiness == Crackiness.Level.NONE) return;
        Identifier texture = state.crackiness == Crackiness.Level.HIGH ? HIGH : state.crackiness == Crackiness.Level.MEDIUM ? MEDIUM : LOW;
        int overlay = LivingEntityRenderer.getOverlayCoords(state, 0.0F);
        collector.order(1).submitModel(getParentModel(), state, poseStack, RenderTypes.entityTranslucent(texture), packedLight, overlay, 0x80FFFFFF, null, state.outlineColor, null);
    }
}
''')

write('entity/layer/GolemFlowerLayer.java', r'''package com.mcmoddev.golems.client.entity.layer;

import com.mcmoddev.golems.client.entity.GolemModel;
import com.mcmoddev.golems.client.entity.GolemRenderState;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.client.renderer.texture.OverlayTexture;

public class GolemFlowerLayer extends RenderLayer<GolemRenderState, GolemModel> {
    public GolemFlowerLayer(RenderLayerParent<GolemRenderState, GolemModel> parent) { super(parent); }

    @Override
    public void submit(PoseStack poseStack, SubmitNodeCollector collector, int packedLight, GolemRenderState state, float yRot, float xRot) {
        if (state.flowerBlock.isEmpty()) return;
        poseStack.pushPose();
        ModelPart arm = getParentModel().getFlowerHoldingArm();
        arm.translateAndRotate(poseStack);
        poseStack.translate(-1.1875F, 1.0625F, -0.9375F);
        poseStack.translate(0.5F, 0.5F, 0.5F);
        poseStack.scale(0.5F, 0.5F, 0.5F);
        poseStack.mulPose(Axis.XP.rotationDegrees(-90.0F));
        poseStack.translate(-0.5F, -0.5F, -0.5F);
        state.flowerBlock.submit(poseStack, collector, packedLight, OverlayTexture.NO_OVERLAY, state.outlineColor);
        poseStack.popPose();
    }
}
''')

write('entity/layer/GolemKittyLayer.java', r'''package com.mcmoddev.golems.client.entity.layer;

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

public class GolemKittyLayer extends RenderLayer<GolemRenderState, GolemModel> {
    private static final Identifier TEXTURE = Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "textures/entity/golem/layer/kitty_layer.png");
    public GolemKittyLayer(RenderLayerParent<GolemRenderState, GolemModel> parent) { super(parent); }

    @Override
    public void submit(PoseStack poseStack, SubmitNodeCollector collector, int packedLight, GolemRenderState state, float yRot, float xRot) {
        if (!state.kittyVisible || state.isInvisibleToPlayer) return;
        getParentModel().setupKittyAnim(state);
        int overlay = LivingEntityRenderer.getOverlayCoords(state, 0.0F);
        collector.order(1).submitModelPart(getParentModel().getKitty(), poseStack, RenderTypes.entityCutout(TEXTURE), packedLight, overlay, null, false, false, 0xFFFFFFFF, null, state.outlineColor);
    }
}
''')

write('entity/layer/GolemBannerLayer.java', r'''package com.mcmoddev.golems.client.entity.layer;

import com.mcmoddev.golems.client.entity.GolemModel;
import com.mcmoddev.golems.client.entity.GolemRenderState;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.util.Mth;

public class GolemBannerLayer extends RenderLayer<GolemRenderState, GolemModel> {
    public GolemBannerLayer(RenderLayerParent<GolemRenderState, GolemModel> parent) { super(parent); }

    @Override
    public void submit(PoseStack poseStack, SubmitNodeCollector collector, int packedLight, GolemRenderState state, float yRot, float xRot) {
        if (state.bannerItem.isEmpty()) return;
        poseStack.pushPose();
        poseStack.translate(0.0F, 0.5825F, 0.3F);
        poseStack.mulPose(Axis.XP.rotationDegrees(180.0F));
        poseStack.mulPose(Axis.YP.rotationDegrees(90.0F));
        float bannerSwing = 0.1F + Mth.cos(state.ageInTicks * 0.07F) * (state.walkAnimationSpeed + 0.1F) * 0.2F;
        poseStack.translate(0.0F, 1.5F, 0.0625F);
        poseStack.mulPose(Axis.ZP.rotation(bannerSwing));
        poseStack.translate(0.0F, -1.5F, -0.0625F);
        poseStack.scale(2.6F, 2.3F, 2.6F);
        getParentModel().root().translateAndRotate(poseStack);
        state.bannerItem.submit(poseStack, collector, packedLight, OverlayTexture.NO_OVERLAY, state.outlineColor);
        poseStack.popPose();
    }
}
''')

print('Applied pass 4 renderer architecture migration.')
