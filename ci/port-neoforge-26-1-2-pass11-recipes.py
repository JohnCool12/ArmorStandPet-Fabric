from pathlib import Path
import json

# --- Minecraft 26.1 recipe syntax ---
root = Path('project/src/main/resources/data/golems/recipe')
recipes = {
    'golem_head.json': {
        'type': 'minecraft:crafting_shapeless',
        'category': 'misc',
        'ingredients': ['minecraft:carved_pumpkin', 'golems:golem_spell'],
        'result': {'id': 'golems:golem_head'},
    },
    'guide_book.json': {
        'type': 'minecraft:crafting_shapeless',
        'category': 'misc',
        'ingredients': ['minecraft:book', ['minecraft:pumpkin', 'minecraft:carved_pumpkin']],
        'result': {'id': 'golems:guide_book'},
    },
    'golem_spell.json': {
        'type': 'minecraft:crafting_shapeless',
        'category': 'misc',
        'ingredients': ['minecraft:feather', 'minecraft:redstone', 'minecraft:paper', 'minecraft:ink_sac'],
        'result': {'id': 'golems:golem_spell', 'count': 3},
    },
}
for name, data in recipes.items():
    p = root / name
    if not p.exists():
        raise SystemExit(f'Missing expected recipe: {p}')
    p.write_text(json.dumps(data, indent=2) + '\n')

# Invariant: 26.1 ingredients are identifiers/tags or lists of identifiers, never old {item: ...} objects.
for p in root.glob('*.json'):
    data = json.loads(p.read_text())
    for ingredient in data.get('ingredients', []):
        if isinstance(ingredient, dict) and 'item' in ingredient:
            raise SystemExit(f'Old ingredient object remains in {p}: {ingredient}')
        if isinstance(ingredient, list) and any(isinstance(v, dict) for v in ingredient):
            raise SystemExit(f'Old alternative ingredient object remains in {p}')

# --- Minecraft 26.1 client-item definitions ---
# 1.21.4+ / 26.1 requires assets/<namespace>/items/<id>.json in addition to models/item.
items_root = Path('project/src/main/resources/assets/golems/items')
items_root.mkdir(parents=True, exist_ok=True)
for item_id in ('golem_head', 'golem_spell', 'guide_book', 'spawn_bedrock_golem'):
    (items_root / f'{item_id}.json').write_text(json.dumps({
        'model': {
            'type': 'minecraft:model',
            'model': f'golems:item/{item_id}',
        }
    }, indent=2) + '\n')

# The generic Golem Spawn Egg had neither a model nor a client-item definition.
# Use Minecraft's spawn-egg template with static neutral/pumpkin tints; no generated image is needed.
models_root = Path('project/src/main/resources/assets/golems/models/item')
models_root.mkdir(parents=True, exist_ok=True)
(models_root / 'golem_spawn_egg.json').write_text(json.dumps({
    'parent': 'minecraft:item/template_spawn_egg',
}, indent=2) + '\n')
(items_root / 'golem_spawn_egg.json').write_text(json.dumps({
    'model': {
        'type': 'minecraft:model',
        'model': 'golems:item/golem_spawn_egg',
        'tints': [
            {'type': 'minecraft:constant', 'value': 10987431},
            {'type': 'minecraft:constant', 'value': 15105570},
        ],
    }
}, indent=2) + '\n')

# --- Random Golem Spawn Egg behavior ---
random_item = Path('project/src/main/java/com/mcmoddev/golems/item/RandomGolemSpawnEggItem.java')
random_item.write_text(r'''package com.mcmoddev.golems.item;

import com.mcmoddev.golems.EGRegistry;
import com.mcmoddev.golems.data.golem.Golem;
import com.mcmoddev.golems.entity.GolemBase;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Registry;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

import java.util.List;

/**
 * Spawn egg that chooses one concrete Extra Golems material on every use.
 * Internal generic_* parent/template entries and the Bedrock Golem are never selected.
 */
public final class RandomGolemSpawnEggItem extends Item {

    public RandomGolemSpawnEggItem(final Item.Properties properties) {
        super(properties);
    }

    @Override
    public InteractionResult useOn(final UseOnContext context) {
        final Level level = context.getLevel();
        final BlockPos clickedPos = context.getClickedPos();
        final ItemStack stack = context.getItemInHand();
        final Player player = context.getPlayer();

        final BlockState clickedState = level.getBlockState(clickedPos);
        final BlockPos spawnPos = clickedState.getBlockSupportShape(level, clickedPos).isEmpty()
                ? clickedPos
                : clickedPos.relative(context.getClickedFace());

        if (level instanceof ServerLevel serverLevel) {
            final Registry<Golem> registry = serverLevel.registryAccess().lookupOrThrow(EGRegistry.Keys.GOLEM);
            final List<Identifier> candidates = registry.keySet().stream()
                    .filter(id -> !id.getPath().startsWith("generic_") && !id.getPath().equals("bedrock"))
                    .toList();

            if (candidates.isEmpty()) {
                return InteractionResult.FAIL;
            }

            final Identifier selected = candidates.get(serverLevel.getRandom().nextInt(candidates.size()));
            final GolemBase golem = GolemBase.create(serverLevel, selected);
            golem.snapTo(spawnPos.getX() + 0.5D, spawnPos.getY(), spawnPos.getZ() + 0.5D);
            golem.finalizeSpawn(serverLevel, serverLevel.getCurrentDifficultyAt(spawnPos),
                    EntitySpawnReason.SPAWN_ITEM_USE, null);
            serverLevel.addFreshEntity(golem);

            if (player == null || !player.isCreative()) {
                stack.shrink(1);
            }
        }

        SpawnGolemItem.spawnParticles(level, spawnPos.getX() + 0.5D, spawnPos.getY() + 0.5D,
                spawnPos.getZ() + 0.5D, 0.12D);
        return InteractionResult.SUCCESS;
    }
}
''')

registry_file = Path('project/src/main/java/com/mcmoddev/golems/EGRegistry.java')
registry_text = registry_file.read_text()
if 'import com.mcmoddev.golems.item.RandomGolemSpawnEggItem;' not in registry_text:
    registry_text = registry_text.replace(
        'import com.mcmoddev.golems.item.GuideBookItem;\n',
        'import com.mcmoddev.golems.item.GuideBookItem;\nimport com.mcmoddev.golems.item.RandomGolemSpawnEggItem;\n',
    )
old = '''\t\tpublic static final DeferredHolder<Item, SpawnEggItem> GOLEM_SPAWN_EGG = ITEMS.register("golem_spawn_egg",
\t\t\t\t() -> new SpawnEggItem(new Item.Properties().spawnEgg(EntityReg.GOLEM.get())
\t\t\t\t\t\t.setId(ResourceKey.create(Registries.ITEM, Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "golem_spawn_egg")))));'''
new = '''\t\tpublic static final DeferredHolder<Item, RandomGolemSpawnEggItem> GOLEM_SPAWN_EGG = ITEMS.register("golem_spawn_egg",
\t\t\t\t() -> new RandomGolemSpawnEggItem(new Item.Properties()
\t\t\t\t\t\t.setId(ResourceKey.create(Registries.ITEM, Identifier.fromNamespaceAndPath(ExtraGolems.MODID, "golem_spawn_egg")))));'''
if old not in registry_text:
    raise SystemExit('Could not find the expected vanilla SpawnEggItem GOLEM_SPAWN_EGG registration')
registry_text = registry_text.replace(old, new)
registry_text = registry_text.replace('import net.minecraft.world.item.SpawnEggItem;\n', '')
registry_file.write_text(registry_text)

# Static invariants for the fix.
assert (models_root / 'golem_spawn_egg.json').exists()
assert (items_root / 'golem_spawn_egg.json').exists()
assert 'RandomGolemSpawnEggItem' in registry_file.read_text()
assert 'new SpawnEggItem' not in registry_file.read_text()
assert 'generic_' in random_item.read_text()
assert 'equals("bedrock")' in random_item.read_text()
print('Applied pass 11: recipes, all 26.1 client-item definitions, randomized Golem Spawn Egg behavior, and Bedrock exclusion.')
