from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/client/EGClientEvents.java')
s = p.read_text()

# Register resource reload work through NeoForge's client reload-listener event.
# Minecraft.getInstance() is deliberately unavailable while the mod constructor
# runs in 26.1.2, so touching the singleton from register() crashes bootstrap.
s = s.replace('import com.mcmoddev.golems.EGRegistry;\n',
              'import com.mcmoddev.golems.EGRegistry;\nimport com.mcmoddev.golems.ExtraGolems;\n')
s = s.replace('import net.minecraft.client.resources.model.ModelBakery;\n', '')
s = s.replace('import net.minecraft.server.packs.resources.ReloadableResourceManager;\n', '')
s = s.replace('import net.minecraft.resources.Identifier;\n', '')
if 'import net.minecraft.resources.Identifier;' not in s:
    s = s.replace('import net.minecraft.client.Minecraft;\n',
                  'import net.minecraft.client.Minecraft;\nimport net.minecraft.resources.Identifier;\n')
if 'import net.neoforged.neoforge.client.event.AddClientReloadListenersEvent;' not in s:
    s = s.replace('import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;\n',
                  'import net.neoforged.neoforge.client.event.AddClientReloadListenersEvent;\nimport net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;\n')

s = s.replace('\t\tmodEventBus.register(EGClientEvents.ModHandler.class);\n\t\tModHandler.addResources();\n',
              '\t\tmodEventBus.register(EGClientEvents.ModHandler.class);\n')

old = '''\t\tpublic static void addResources() {\n\t\t\tResourceManager resourceManager = Minecraft.getInstance().getResourceManager();\n\t\t\tif (resourceManager instanceof ReloadableResourceManager) {\n\t\t\t\t// reload dynamic texture map\n\t\t\t\t((ReloadableResourceManager) resourceManager).registerReloadListener(new SimplePreparableReloadListener<ModelBakery>() {\n\t\t\t\t\t@Override\n\t\t\t\t\tprotected ModelBakery prepare(ResourceManager arg0, ProfilerFiller arg1) {\n\t\t\t\t\t\treturn null;\n\t\t\t\t\t}\n\n\t\t\t\t\t@Override\n\t\t\t\t\tprotected void apply(ModelBakery arg0, ResourceManager arg1, ProfilerFiller arg2) {\n\t\t\t\t\t\tGolemRenderType.reloadDynamicTextureMap();\n\t\t\t\t\t}\n\n\t\t\t\t\t@Override\n\t\t\t\t\tpublic String getName() {\n\t\t\t\t\t\treturn "Extra Golems textures";\n\t\t\t\t\t}\n\t\t\t\t});\n\t\t\t}\n\t\t}\n'''
new = '''\t\t@SubscribeEvent\n\t\tpublic static void addResources(final AddClientReloadListenersEvent event) {\n\t\t\tevent.addListener(Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "dynamic_textures"),\n\t\t\t\t\tnew SimplePreparableReloadListener<Void>() {\n\t\t\t\t\t\t@Override\n\t\t\t\t\t\tprotected Void prepare(ResourceManager resourceManager, ProfilerFiller profiler) {\n\t\t\t\t\t\t\treturn null;\n\t\t\t\t\t\t}\n\n\t\t\t\t\t\t@Override\n\t\t\t\t\t\tprotected void apply(Void ignored, ResourceManager resourceManager, ProfilerFiller profiler) {\n\t\t\t\t\t\t\tGolemRenderType.reloadDynamicTextureMap();\n\t\t\t\t\t\t}\n\n\t\t\t\t\t\t@Override\n\t\t\t\t\t\tpublic String getName() {\n\t\t\t\t\t\t\treturn "Extra Golems textures";\n\t\t\t\t\t\t}\n\t\t\t\t\t});\n\t\t}\n'''
if old not in s:
    raise SystemExit('Expected early Minecraft resource-manager registration block was not found')
s = s.replace(old, new)

# Hard invariant: mod construction must not access the Minecraft singleton.
register_start = s.index('public static void register(IEventBus modEventBus)')
register_end = s.index('\n\t}', register_start)
assert 'Minecraft.getInstance()' not in s[register_start:register_end]
assert 'AddClientReloadListenersEvent' in s
assert 'event.addListener(' in s

p.write_text(s)
print('Applied pass 9: defer client resource listener registration to AddClientReloadListenersEvent.')
