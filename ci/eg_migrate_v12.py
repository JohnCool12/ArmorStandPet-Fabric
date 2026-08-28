#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else 'work').resolve()

# Minecraft 26.1 vanilla Ingredient JSON is a string (or #tag string), not
# the pre-26.1 {"item": ...}/{"tag": ...} object used by the upstream 1.21.1 recipes.
recipe_dir = ROOT / 'src/main/resources/data/golems/recipe'
for p in sorted(recipe_dir.glob('*.json')):
    data = json.loads(p.read_text())
    ingredients = data.get('ingredients')
    if isinstance(ingredients, list):
        converted = []
        for ingredient in ingredients:
            if isinstance(ingredient, dict) and set(ingredient) == {'item'}:
                converted.append(ingredient['item'])
            elif isinstance(ingredient, dict) and set(ingredient) == {'tag'}:
                converted.append('#' + ingredient['tag'])
            else:
                converted.append(ingredient)
        data['ingredients'] = converted
    p.write_text(json.dumps(data, indent=2) + '\n')

# FormatterLogger uses printf semantics; concatenate the runtime values so the
# CI gate sees the actual state rather than literal {} placeholders.
events = ROOT / 'src/main/java/com/mcmoddev/golems/EGEvents.java'
s = events.read_text()
old = '''\t\t\t\tExtraGolems.LOGGER.info("[EGPORT] golem_count={} diamond_tag={} diamond_match={}",\n\t\t\t\t\t\tcount, diamondTagged, diamondMatch == null ? "null" : diamondMatch.identifier());\n'''
new = '''\t\t\t\tExtraGolems.LOGGER.info("[EGPORT] golem_count=" + count\n\t\t\t\t\t\t+ " diamond_tag=" + diamondTagged\n\t\t\t\t\t\t+ " diamond_match=" + (diamondMatch == null ? "null" : diamondMatch.identifier()));\n'''
if old not in s:
    raise SystemExit('Expected EGPORT formatter log was not found')
events.write_text(s.replace(old, new))

print('Applied Minecraft 26.1 recipe migration + observable construction self-test pass 12')
