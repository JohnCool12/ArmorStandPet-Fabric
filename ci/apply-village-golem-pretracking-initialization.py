from pathlib import Path
import re

root = Path('project')
golem_path = root / 'src/main/java/com/mcmoddev/golems/entity/GolemBase.java'
mixin_path = root / 'src/main/java/com/mcmoddev/golems/mixin/VillagerMixin.java'

golem = golem_path.read_text()
mixin = mixin_path.read_text()

# The vanilla SpawnUtil/LargeEntitySpawnHelper creates the entity internally and adds the
# successful candidate to the ServerLevel before returning Optional<T>.  The old mixin
# therefore assigned the material ID too late.  A tiny server-thread ThreadLocal lets the
# GolemBase constructor see the chosen material while SpawnUtil is constructing candidate
# entities, without replacing any of SpawnUtil's placement/spawn-validation behavior.
class_anchor = 'public class GolemBase extends IronGolem implements IExtraGolem {'
if golem.count(class_anchor) != 1:
    raise SystemExit(f'GolemBase class anchor count={golem.count(class_anchor)}')
field_block = '''public class GolemBase extends IronGolem implements IExtraGolem {\n\n\t/**\n\t * Material selected for a villager-summoned replacement while SpawnUtil is constructing\n\t * candidate entities. SpawnUtil owns construction/placement and can expose the successful\n\t * entity to world tracking before returning, so the material must be initialized from the\n\t * constructor rather than from Optional.ifPresent(...) after SpawnUtil returns.\n\t */\n\tprivate static final ThreadLocal<ResourceLocation> PENDING_VILLAGE_SUMMON_GOLEM_ID = new ThreadLocal<>();'''
golem = golem.replace(class_anchor, field_block, 1)

# Insert scoped setters before the constructor. ResourceLocation is already used throughout
# GolemBase, so no new Minecraft import is required. ThreadLocal is java.lang.
constructor_match = re.search(r'\n\tpublic GolemBase\s*\(', golem)
if not constructor_match:
    raise SystemExit('GolemBase constructor not found')
methods = '''\n\tpublic static void beginVillageSummonInitialization(final ResourceLocation golemId) {\n\t\tif (golemId == null) {\n\t\t\tthrow new IllegalArgumentException("Village-summoned Extra Golem ID cannot be null");\n\t\t}\n\t\tPENDING_VILLAGE_SUMMON_GOLEM_ID.set(golemId);\n\t}\n\n\tpublic static void endVillageSummonInitialization() {\n\t\tPENDING_VILLAGE_SUMMON_GOLEM_ID.remove();\n\t}\n'''
golem = golem[:constructor_match.start()] + methods + golem[constructor_match.start():]

# Insert material initialization at the END of the constructor, after GolemBase instance
# fields such as behaviorData have been initialized. setGolemId() uses those fields.
constructor_match = re.search(r'\n\tpublic GolemBase\s*\(', golem)
start = constructor_match.start() + 1
brace = golem.find('{', constructor_match.start())
if brace < 0:
    raise SystemExit('GolemBase constructor opening brace missing')
depth = 0
end_brace = None
for i in range(brace, len(golem)):
    if golem[i] == '{': depth += 1
    elif golem[i] == '}':
        depth -= 1
        if depth == 0:
            end_brace = i
            break
if end_brace is None:
    raise SystemExit('GolemBase constructor closing brace missing')
constructor_body = golem[brace:end_brace]
if 'PENDING_VILLAGE_SUMMON_GOLEM_ID.get()' in constructor_body:
    raise SystemExit('Pending village initialization already present in constructor')
constructor_insert = '''\n\t\tfinal ResourceLocation pendingVillageGolemId = PENDING_VILLAGE_SUMMON_GOLEM_ID.get();\n\t\tif (pendingVillageGolemId != null) {\n\t\t\tsetGolemId(pendingVillageGolemId);\n\t\t}\n\t'''
golem = golem[:end_brace] + constructor_insert + golem[end_brace:]

golem_path.write_text(golem)

# Locate the replacement branch in VillagerMixin by the old post-spawn material assignment.
id_match = re.search(r'(?m)^\s*([A-Za-z_$][A-Za-z0-9_$]*)\.setGolemId\(([^;]+)\);\s*$', mixin)
if not id_match:
    raise SystemExit('VillagerMixin post-spawn setGolemId call not found')
golem_var = id_match.group(1)
id_expr = id_match.group(2).strip()

# Find the declaration containing SpawnUtil.trySpawnMob immediately before that lambda.
helper_pos = mixin.rfind('SpawnUtil.trySpawnMob(', 0, id_match.start())
if helper_pos < 0:
    raise SystemExit('VillagerMixin replacement SpawnUtil.trySpawnMob call not found')
line_start = mixin.rfind('\n', 0, helper_pos) + 1

# Find the return statement for the Optional returned by that replacement branch.
return_match = re.search(r'(?m)^\s*return\s+[^;]+;\s*$', mixin[id_match.end():])
if not return_match:
    raise SystemExit('VillagerMixin replacement return after spawn not found')
return_start = id_match.end() + return_match.start()
return_end = id_match.end() + return_match.end()

# Remove only the too-late setGolemId statement from the lambda. Keep setHealth(maxHealth),
# which is still useful because material attributes are now established before finalization.
mixin = mixin[:id_match.start()] + mixin[id_match.end():]
removed = id_match.end() - id_match.start()
return_start -= removed
return_end -= removed

# Scope the pending material around SpawnUtil itself. A finally block guarantees no state
# leaks to unrelated entity creation even if SpawnUtil throws or returns Optional.empty().
indent_match = re.match(r'[\t ]*', mixin[line_start:])
indent = indent_match.group(0)
begin = f'{indent}GolemBase.beginVillageSummonInitialization({id_expr});\n{indent}try {{\n'
mixin = mixin[:line_start] + begin + mixin[line_start:]
added = len(begin)
return_start += added
return_end += added

# Indent the original spawn/ifPresent/return block one extra tab for readability.
block = mixin[line_start + added:return_end]
block = ''.join(('\t' + line if line.strip() else line) for line in block.splitlines(True))
mixin = mixin[:line_start + added] + block + mixin[return_end:]
return_end = line_start + added + len(block)
finally_block = f'\n{indent}}} finally {{\n{indent}\tGolemBase.endVillageSummonInitialization();\n{indent}}}'
mixin = mixin[:return_end] + finally_block + mixin[return_end:]

# Strong source-level invariants.
method_pos = mixin.find('golems$replaceVillageGolem')
if method_pos < 0:
    raise SystemExit('replacement method disappeared')
method_brace = mixin.find('{', method_pos)
depth = 0
method_end = None
for i in range(method_brace, len(mixin)):
    if mixin[i] == '{': depth += 1
    elif mixin[i] == '}':
        depth -= 1
        if depth == 0:
            method_end = i + 1
            break
method = mixin[method_pos:method_end]
if '.setGolemId(' in method:
    raise SystemExit('VillagerMixin still assigns material after SpawnUtil returns')
if method.find('GolemBase.beginVillageSummonInitialization(') > method.find('SpawnUtil.trySpawnMob('):
    raise SystemExit('Pending material is not established before SpawnUtil call')
if 'GolemBase.endVillageSummonInitialization();' not in method:
    raise SystemExit('Pending material cleanup missing')

mixin_path.write_text(mixin)
print('Applied pre-tracking material initialization for villager-summoned Extra Golems.')
