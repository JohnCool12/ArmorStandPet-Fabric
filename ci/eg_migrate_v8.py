#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else 'work').resolve()
SRC = ROOT / 'src/main/java'

def patch(rel, pairs):
    p = SRC / rel
    s = p.read_text()
    for old, new in pairs:
        if old not in s:
            raise SystemExit(f'Missing expected text in {rel}: {old[:120]!r}')
        s = s.replace(old, new)
    p.write_text(s)

def ensure_import(rel, imp):
    p = SRC / rel
    s = p.read_text()
    line = f'import {imp};\n'
    if line not in s:
        pkg_end = s.index('\n', s.index('package ')) + 1
        s = s[:pkg_end] + '\n' + line + s[pkg_end:]
        p.write_text(s)

# Recreate the small client registry helper removed by the broad legacy-client cleanup.
client_utils = SRC / 'com/mcmoddev/golems/client/ClientUtils.java'
client_utils.parent.mkdir(parents=True, exist_ok=True)
client_utils.write_text('''package com.mcmoddev.golems.client;\n\nimport net.minecraft.client.Minecraft;\nimport net.minecraft.core.RegistryAccess;\nimport net.minecraft.world.entity.player.Player;\nimport net.minecraft.world.level.Level;\n\nimport java.util.Optional;\n\npublic final class ClientUtils {\n    private ClientUtils() {}\n\n    public static Optional<Level> getClientLevel() {\n        return Optional.ofNullable(Minecraft.getInstance().level);\n    }\n\n    public static Optional<Player> getClientPlayer() {\n        return Optional.ofNullable(Minecraft.getInstance().player);\n    }\n\n    public static Optional<RegistryAccess> getClientRegistryAccess() {\n        return getClientLevel().map(Level::registryAccess);\n    }\n}\n''')

# GolemBase: preserve per-golem death loot by overriding the non-final drop hook and
# explicitly supplying the data-driven loot key; migrate crafting remainder and level side check.
patch('com/mcmoddev/golems/entity/GolemBase.java', [
    ('''\t@Override\n\tpublic Optional<ResourceKey<net.minecraft.world.level.storage.loot.LootTable>> getLootTable() {\n\t\tfinal Optional<GolemContainer> oContainer = getContainer();\n\t\tif (oContainer.isEmpty()) {\n\t\t\treturn super.getLootTable();\n\t\t}\n\t\treturn Optional.of(ResourceKey.create(net.minecraft.core.registries.Registries.LOOT_TABLE, oContainer.get().getLootTable()));\n\t}\n''', '''\t@Override\n\tprotected void dropFromLootTable(final ServerLevel level, final DamageSource source, final boolean playerKilled) {\n\t\tfinal Optional<GolemContainer> oContainer = getContainer();\n\t\tif (oContainer.isEmpty()) {\n\t\t\tsuper.dropFromLootTable(level, source, playerKilled);\n\t\t\treturn;\n\t\t}\n\t\tfinal ResourceKey<net.minecraft.world.level.storage.loot.LootTable> lootKey =\n\t\t\t\tResourceKey.create(net.minecraft.core.registries.Registries.LOOT_TABLE, oContainer.get().getLootTable());\n\t\tthis.dropFromLootTable(level, source, playerKilled, lootKey);\n\t}\n'''),
    ('player.setItemInHand(hand, stack.getCraftingRemainder());', 'player.setItemInHand(hand, java.util.Optional.ofNullable(stack.getCraftingRemainder()).map(net.minecraft.world.item.ItemStackTemplate::create).orElse(ItemStack.EMPTY));'),
    ('if (!this.level().isClientSide) {', 'if (!this.level().isClientSide()) {'),
])

# Straight 26.1 entity/item/tag API renames.
patch('com/mcmoddev/golems/data/behavior/ExplodeBehavior.java', [
    ('mob.isInWaterRainOrBubble()', 'mob.isInWaterOrRain()'),
    ('tag.getCompound(KEY_EXPLOSION_HELPER)', 'tag.getCompound(KEY_EXPLOSION_HELPER).orElseGet(CompoundTag::new)'),
])
patch('com/mcmoddev/golems/data/behavior/FollowBehavior.java', [
    ('e -> e.codec().equals(this.entity)', 'e -> e.getType().equals(this.entity)'),
])
patch('com/mcmoddev/golems/data/behavior/ItemUpdateGolemBehavior.java', [
    ('item.getItemHolder()', 'item.typeHolder()'),
    ('randomItem.getDescription()', 'randomItem.getName(randomItem.getDefaultInstance())'),
])
patch('com/mcmoddev/golems/data/behavior/AbstractShootBehavior.java', [
    ('mob.canAttackType(e.codec())', 'mob.canAttackType(e.getType())'),
])
patch('com/mcmoddev/golems/data/behavior/TemptBehavior.java', [
    ('value.left().get().identifier()', 'value.left().get().location()'),
    ('randomItem.getDescription()', 'randomItem.getName(randomItem.getDefaultInstance())'),
])
patch('com/mcmoddev/golems/EGEvents.java', [
    ('entity.codec() == EntityType.IRON_GOLEM', 'entity.getType() == EntityType.IRON_GOLEM'),
])
patch('com/mcmoddev/golems/menu/GolemCraftingMenu.java', [
    ('return super.codec();', 'return super.getType();'),
])

# Crafting remainder is now a nullable ItemStackTemplate rather than an ItemStack.
patch('com/mcmoddev/golems/data/behavior/UseFuelBehavior.java', [
    ('stack = stack.getCraftingRemainder();', 'stack = java.util.Optional.ofNullable(stack.getCraftingRemainder()).map(net.minecraft.world.item.ItemStackTemplate::create).orElse(ItemStack.EMPTY);'),
    ('player.setItemInHand(hand, stack.getCraftingRemainder());', 'player.setItemInHand(hand, java.util.Optional.ofNullable(stack.getCraftingRemainder()).map(net.minecraft.world.item.ItemStackTemplate::create).orElse(ItemStack.EMPTY));'),
])

# ServerLevel moved/was not imported in these migrated call sites.
for rel in [
    'com/mcmoddev/golems/data/behavior/WearBannerBehavior.java',
    'com/mcmoddev/golems/data/behavior/ShootSnowballsBehavior.java',
    'com/mcmoddev/golems/data/behavior/SplitBehavior.java',
    'com/mcmoddev/golems/data/behavior/SetFireBehavior.java',
    'com/mcmoddev/golems/data/behavior/util/TargetedMobEffects.java',
    'com/mcmoddev/golems/entity/goal/MoveToItemGoal.java',
]:
    ensure_import(rel, 'net.minecraft.server.level.ServerLevel')

print('Applied 26.1.2 semantic migration pass 8')
