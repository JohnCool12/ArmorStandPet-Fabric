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

# Keep the final workflow sequence stable while layering the dispenser AI refinement after
# the renderer fix. This pass is intentionally chained here because pass 12 is the final
# explicitly-invoked migration stage in the release workflow.
pass13 = Path('ci/port-neoforge-26-1-2-pass13-dispenser-warden-ranged.py')
exec(compile(pass13.read_text(), str(pass13), 'exec'))

# Apply the ranged-positioning refinement after the projectile/timing expansion.
pass14 = Path('ci/port-neoforge-26-1-2-pass14-dispenser-fluid-ranged-position.py')
exec(compile(pass14.read_text(), str(pass14), 'exec'))

# Finalize the loaded ranged mode and potion spacing.
pass15 = Path('ci/port-neoforge-26-1-2-pass15-dispenser-ranged-only-loaded.py')
exec(compile(pass15.read_text(), str(pass15), 'exec'))

# Restore instantaneous melee when a close target is actually strikeable, while
# immediately falling back to ranged for close-but-unreachable targets.
pass16 = Path('ci/port-neoforge-26-1-2-pass16-dispenser-instant-melee-ranged-switch.py')
exec(compile(pass16.read_text(), str(pass16), 'exec'))

# Keep the expanded ranged detection only while the dispenser has usable projectile ammo;
# empty/unshootable mode should use the underlying vanilla-style Iron Golem detection range.
pass17 = Path('ci/port-neoforge-26-1-2-pass17-dispenser-dynamic-detection-range.py')
exec(compile(pass17.read_text(), str(pass17), 'exec'))

# Potion throws need a real hard range gate so the golem does not waste slow lobbed
# projectiles before getting close enough for them to land reliably.
pass18 = Path('ci/port-neoforge-26-1-2-pass18-dispenser-potion-hard-range.py')
exec(compile(pass18.read_text(), str(pass18), 'exec'))

# Ranged cooldown must be global to the golem's firing cycle. Damage/retaliation can
# retarget the golem and must never reset the last-shot timestamp or create a free shot.
pass19 = Path('ci/port-neoforge-26-1-2-pass19-dispenser-preserve-shot-cooldown-on-retarget.py')
exec(compile(pass19.read_text(), str(pass19), 'exec'))

# Allow explicit external player targets (e.g. Mob Battle Enrager control) to reach the
# normal Mob#setTarget path instead of being vetoed before the external controller can act.
pass20 = Path('ci/port-neoforge-26-1-2-pass20-mobbattle-player-target-compat.py')
exec(compile(pass20.read_text(), str(pass20), 'exec'))
