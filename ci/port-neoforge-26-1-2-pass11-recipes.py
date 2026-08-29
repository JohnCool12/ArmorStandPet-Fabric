from pathlib import Path
import json

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
print('Applied pass 11: migrated all Extra Golems crafting recipes to Minecraft 26.1 syntax.')
