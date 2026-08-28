#!/usr/bin/env python3
from pathlib import Path
import re, subprocess, sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else 'work').resolve()
SRC = ROOT / 'src/main/java'
CLIENT = SRC / 'com/mcmoddev/golems/client'

# Pass 3 intentionally replaced the entire client tree with a compile-only renderer.
# Restore the upstream client implementation so the 26.1 port preserves the actual
# model, all material/override/cosmetic layers, inventory screen and guide book UI.
subprocess.run(['git', 'checkout', 'HEAD', '--', 'src/main/java/com/mcmoddev/golems/client'], cwd=ROOT, check=True)

# Apply the broad 26.1 naming/package migrations that originally happened before
# the pass-3 client deletion.
for p in CLIENT.rglob('*.java'):
    s = p.read_text()
    s = s.replace('net.minecraft.resources.ResourceLocation', 'net.minecraft.resources.Identifier')
    s = re.sub(r'\bResourceLocation\b', 'Identifier', s)
    s = s.replace('net.minecraft.client.model.IronGolemModel', 'net.minecraft.client.model.animal.golem.IronGolemModel')
    s = s.replace('net.minecraft.client.renderer.RenderType', 'net.minecraft.client.renderer.rendertype.RenderType')
    s = s.replace('Identifier.fromNamespaceAndPath', 'Identifier.fromNamespaceAndPath')
    s = s.replace('Identifier.parse(', 'Identifier.parse(')
    s = s.replace('.location()', '.identifier()')
    p.write_text(s)

# Keep the already-validated 26.1 ClientUtils implementation from semantic pass 8.
(CLIENT / 'ClientUtils.java').write_text('''package com.mcmoddev.golems.client;\n\nimport net.minecraft.client.Minecraft;\nimport net.minecraft.core.RegistryAccess;\nimport net.minecraft.world.entity.player.Player;\nimport net.minecraft.world.level.Level;\n\nimport java.util.Optional;\n\npublic final class ClientUtils {\n    private ClientUtils() {}\n    public static Optional<Level> getClientLevel() { return Optional.ofNullable(Minecraft.getInstance().level); }\n    public static Optional<Player> getClientPlayer() { return Optional.ofNullable(Minecraft.getInstance().player); }\n    public static Optional<RegistryAccess> getClientRegistryAccess() { return getClientLevel().map(Level::registryAccess); }\n}\n''')

# Reconnect GuideBookItem to the restored client GUI without touching Minecraft
# client classes on a dedicated server.
guide = SRC / 'com/mcmoddev/golems/item/GuideBookItem.java'
g = guide.read_text()
if 'com.mcmoddev.golems.client.EGClientEvents' not in g:
    pkg_end = g.index('\n', g.index('package ')) + 1
    g = g[:pkg_end] + '\nimport com.mcmoddev.golems.client.EGClientEvents;\n' + g[pkg_end:]
# Pass 3 removed the original client-side GUI opening block. Reinsert it immediately
# after the held stack is captured, using the 26.1 isClientSide() method.
needle = 'ItemStack itemstack = playerIn.getItemInHand(handIn);'
if needle in g and 'EGClientEvents.ForgeHandler.loadBookGui' not in g:
    g = g.replace(needle, needle + '\n\t\tif (worldIn.isClientSide()) {\n\t\t\tEGClientEvents.ForgeHandler.loadBookGui(playerIn, itemstack);\n\t\t}', 1)
guide.write_text(g)

print('Restored upstream client feature tree for full 26.1 parity compile pass 15')
