#!/usr/bin/env python3
from pathlib import Path
import re, shutil, sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else 'work').resolve()
SRC = ROOT / 'src/main/java'
CLIENT = SRC / 'com/mcmoddev/golems/client'

# ---- Exact 26.1 render-core fixes exposed by pass 16 ----
model = CLIENT / 'entity/GolemModel.java'
s = model.read_text()
s = s.replace('this.ears.copyFrom(this.root().getChild("head"));', '''ModelPart head = this.root().getChild("head");
\t\tthis.ears.x = head.x; this.ears.y = head.y; this.ears.z = head.z;
\t\tthis.ears.xRot = head.xRot; this.ears.yRot = head.yRot; this.ears.zRot = head.zRot;''')
model.write_text(s)

renderer = CLIENT / 'entity/GolemRenderer.java'
s = renderer.read_text()
s = s.replace('entity.level().getDayTime()', 'entity.level().getDefaultClockTime()')
s = s.replace('ExtraGolems.CONFIG.aprilFools()', 'ExtraGolems.CONFIG.aprilFirst()')
renderer.write_text(s)

kitty = CLIENT / 'entity/layer/GolemKittyLayer.java'
s = kitty.read_text().replace('RenderTypes.entityCutoutNoCull(TEXTURE)', 'RenderTypes.entityCutout(TEXTURE)')
kitty.write_text(s)

# Modern client event wiring. Most importantly, do NOT dereference Minecraft during
# mod construction (the exact startup crash from the earlier port). Register model
# layers/renderers/screens through their lifecycle events. Dynamic-texture cache
# reload is hooked through AddClientReloadListenersEvent, which fires during Minecraft
# construction when client resources actually exist.
events = CLIENT / 'EGClientEvents.java'
events.write_text(r'''package com.mcmoddev.golems.client;

import com.mcmoddev.golems.EGRegistry;
import com.mcmoddev.golems.ExtraGolems;
import com.mcmoddev.golems.client.entity.GolemDynamicTextures;
import com.mcmoddev.golems.client.entity.GolemModel;
import com.mcmoddev.golems.client.entity.GolemRenderer;
import com.mcmoddev.golems.client.menu.GolemInventoryScreen;
import com.mcmoddev.golems.client.menu.GuideBookScreen;
import com.mcmoddev.golems.data.GolemContainer;
import net.minecraft.client.Minecraft;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.server.packs.resources.SimplePreparableReloadListener;
import net.minecraft.util.profiling.ProfilerFiller;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.client.event.AddClientReloadListenersEvent;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;
import net.neoforged.neoforge.client.event.EntityRenderersEvent;
import net.neoforged.neoforge.client.event.RegisterMenuScreensEvent;
import net.neoforged.neoforge.common.NeoForge;

public final class EGClientEvents {
    private EGClientEvents() {}

    public static void register(IEventBus modEventBus) {
        NeoForge.EVENT_BUS.register(ForgeHandler.class);
        modEventBus.register(ModHandler.class);
    }

    public static final class ModHandler {
        @SubscribeEvent
        public static void registerScreens(RegisterMenuScreensEvent event) {
            event.register(EGRegistry.MenuReg.GOLEM_INVENTORY.get(), GolemInventoryScreen::new);
        }

        @SubscribeEvent
        public static void registerEntityLayers(EntityRenderersEvent.RegisterLayerDefinitions event) {
            event.registerLayerDefinition(GolemRenderer.GOLEM_MODEL_RESOURCE, GolemModel::createBodyLayer);
        }

        @SubscribeEvent
        public static void registerEntityRenderers(EntityRenderersEvent.RegisterRenderers event) {
            event.registerEntityRenderer(EGRegistry.EntityReg.GOLEM.get(), GolemRenderer::new);
        }

        @SubscribeEvent
        public static void addClientReloadListeners(AddClientReloadListenersEvent event) {
            event.addListener(new SimplePreparableReloadListener<Void>() {
                @Override protected Void prepare(ResourceManager manager, ProfilerFiller profiler) { return null; }
                @Override protected void apply(Void ignored, ResourceManager manager, ProfilerFiller profiler) {
                    GolemDynamicTextures.clear();
                }
                @Override public String getName() { return "Extra Golems dynamic textures"; }
            });
        }
    }

    public static final class ForgeHandler {
        @SubscribeEvent
        public static void onPlayerLoggedOut(ClientPlayerNetworkEvent.LoggingOut event) {
            GolemContainer.reset();
            GolemDynamicTextures.clear();
        }

        public static void loadBookGui(Player player, ItemStack stack) {
            if (!player.level().isClientSide()) return;
            Minecraft.getInstance().setScreen(new GuideBookScreen(player, stack));
        }
    }
}
''')

# For this compile-probe only, isolate the renderer from the large 26.1 GUI API
# migration. A later pass restores and ports the complete menu tree before release.
# Keep the inventory/guide classes as tiny compile stubs so EGClientEvents and
# GuideBookItem remain structurally connected without masking any renderer errors.
menu = CLIENT / 'menu'
shutil.rmtree(menu, ignore_errors=True)
menu.mkdir(parents=True, exist_ok=True)
(menu/'GolemInventoryScreen.java').write_text(r'''package com.mcmoddev.golems.client.menu;
import com.mcmoddev.golems.menu.GolemInventoryMenu;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
public final class GolemInventoryScreen extends AbstractContainerScreen<GolemInventoryMenu> {
 public GolemInventoryScreen(GolemInventoryMenu menu, Inventory inventory, Component title) { super(menu, inventory, title); }
}
''')
(menu/'GuideBookScreen.java').write_text(r'''package com.mcmoddev.golems.client.menu;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
public final class GuideBookScreen extends Screen {
 public GuideBookScreen(Player player, ItemStack stack) { super(Component.translatable("item.golems.guide_book")); }
}
''')

print('Applied 26.1 render-core fixes and isolated GUI compile surface pass 17')
