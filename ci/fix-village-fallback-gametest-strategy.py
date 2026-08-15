from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/test/VillageReplacementFallbackGameTest.java')
s = p.read_text()
s = s.replace('import java.lang.reflect.Method;\n', 'import java.lang.reflect.Field;\nimport java.lang.reflect.Method;\nimport java.lang.reflect.Modifier;\n', 1)
anchor = 'public final class VillageReplacementFallbackGameTest implements FabricGameTest {\n'
helper = '''public final class VillageReplacementFallbackGameTest implements FabricGameTest {\n    private static SpawnUtil.Strategy findIronGolemStrategy() throws Exception {\n        SpawnUtil.Strategy first = null;\n        for (Field field : SpawnUtil.Strategy.class.getDeclaredFields()) {\n            if (!Modifier.isStatic(field.getModifiers()) || !SpawnUtil.Strategy.class.isAssignableFrom(field.getType())) continue;\n            field.setAccessible(true);\n            SpawnUtil.Strategy value = (SpawnUtil.Strategy) field.get(null);\n            if (first == null) first = value;\n            if (field.getName().toLowerCase().contains("iron")) return value;\n        }\n        if (first == null) throw new IllegalStateException("No SpawnUtil.Strategy constants found");\n        return first; // In 1.21.1 the first strategy is the legacy Iron Golem strategy.\n    }\n'''
if s.count(anchor) != 1:
    raise SystemExit('GameTest class anchor missing')
s = s.replace(anchor, helper, 1)
if s.count('SpawnUtil.Strategy.IRON_GOLEM') != 1:
    raise SystemExit('Mapping-specific Strategy.IRON_GOLEM anchor missing')
s = s.replace('SpawnUtil.Strategy.IRON_GOLEM', 'findIronGolemStrategy()', 1)
p.write_text(s)
print('Made village fallback GameTest strategy lookup mapping-independent.')
