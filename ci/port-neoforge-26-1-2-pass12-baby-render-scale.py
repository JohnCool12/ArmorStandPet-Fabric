from pathlib import Path

renderer = Path('project/src/main/java/com/mcmoddev/golems/client/entity/GolemRenderer.java')
s = renderer.read_text()

# V4's original renderer scaled split-off baby golems, but that override was lost when
# porting to Minecraft 26.1's render-state API. The entity already reports isBaby(),
# and LivingEntity computes ageScale from that same baby state for its dimensions.
# Restore the visual transform using ageScale so model size follows the physical baby size.
extract_needle = '''        state.valid = container.isPresent();\n'''
extract_replacement = '''        state.valid = container.isPresent();\n        // Preserve the custom CHILD flag in the 26.1 render state explicitly.\n        // ageScale is Minecraft's baby-size factor used alongside the entity dimensions.\n        state.isBaby = entity.isBaby();\n        state.ageScale = entity.getAgeScale();\n'''
if extract_needle not in s:
    raise SystemExit('Could not locate GolemRenderer render-state extraction anchor')
s = s.replace(extract_needle, extract_replacement, 1)

scale_method = '''\n    @Override\n    protected void scale(GolemRenderState state, PoseStack poseStack) {\n        // Match the rendered baby exactly to Minecraft's baby dimension/age scaling.\n        // This transform wraps the parent model and every render layer (eyes, cracks,\n        // banner, flower, kitty, dynamic/material layers), keeping the whole golem aligned.\n        if (state.isBaby) {\n            final float babyScale = state.ageScale;\n            poseStack.scale(babyScale, babyScale, babyScale);\n        }\n    }\n'''
setup_anchor = '''\n    @Override\n    protected void setupRotations(GolemRenderState state, PoseStack poseStack, float bodyRot, float scale) {\n'''
if setup_anchor not in s:
    raise SystemExit('Could not locate GolemRenderer setupRotations anchor')
if 'protected void scale(GolemRenderState state, PoseStack poseStack)' not in s:
    s = s.replace(setup_anchor, scale_method + setup_anchor, 1)

renderer.write_text(s)

# SplitBehavior is the source of these mini golems and must continue to mark them as babies.
split = Path('project/src/main/java/com/mcmoddev/golems/data/behavior/SplitBehavior.java').read_text()
if 'child.setBaby(true);' not in split:
    raise SystemExit('SplitBehavior no longer marks split children as babies')

# Static release invariants: render-state flag + dynamic ageScale + no arbitrary hard-coded baby factor.
final = renderer.read_text()
for required in (
    'state.isBaby = entity.isBaby();',
    'state.ageScale = entity.getAgeScale();',
    'if (state.isBaby)',
    'final float babyScale = state.ageScale;',
    'poseStack.scale(babyScale, babyScale, babyScale);',
):
    if required not in final:
        raise SystemExit(f'Missing baby render-scale invariant: {required}')

print('Applied pass 12: restored split-child visual scaling from Minecraft baby ageScale to match entity dimensions.')
