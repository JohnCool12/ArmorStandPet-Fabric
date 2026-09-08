from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/test/BedrockNaturalAiGameTest.java')
s = p.read_text()

# Keep every actor close to the GameTest origin so the vanilla control cannot randomly
# land across a chunk boundary and stop ticking depending on the generated test origin.
layout = {
    'new net.minecraft.core.BlockPos(4, 2, 4)': 'new net.minecraft.core.BlockPos(2, 2, 2)',
    'new net.minecraft.core.BlockPos(10, 2, 4)': 'new net.minecraft.core.BlockPos(6, 2, 6)',
    'bedrockAttacker.setPos(bedrock.getX() + 6.0D, bedrock.getY(), bedrock.getZ());': 'bedrockAttacker.setPos(bedrock.getX(), bedrock.getY(), bedrock.getZ() + 4.0D);',
    'vanillaAttacker.setPos(vanilla.getX() + 6.0D, vanilla.getY(), vanilla.getZ());': 'vanillaAttacker.setPos(vanilla.getX(), vanilla.getY(), vanilla.getZ() - 4.0D);',
    'bedrockZombie.moveTo(bedrock.getX() + 4.0D, bedrock.getY(), bedrock.getZ(), 0.0F, 0.0F);': 'bedrockZombie.moveTo(bedrock.getX() + 2.0D, bedrock.getY(), bedrock.getZ(), 0.0F, 0.0F);',
    'vanillaZombie.moveTo(vanilla.getX() + 4.0D, vanilla.getY(), vanilla.getZ(), 0.0F, 0.0F);': 'vanillaZombie.moveTo(vanilla.getX() - 2.0D, vanilla.getY(), vanilla.getZ(), 0.0F, 0.0F);',
}
for old_pos, new_pos in layout.items():
    if old_pos not in s:
        raise SystemExit('Missing compact-layout marker: ' + old_pos)
    s = s.replace(old_pos, new_pos, 1)

old = '''                helper.assertTrue(vanilla.canAttack(vanillaZombie),
                        "Vanilla natural Iron Golem cannot attack the surviving Husk probe");
                helper.assertTrue(bedrock.canAttack(bedrockZombie),
                        "Bedrock cannot attack the surviving Husk probe");
                helper.assertTrue(vanilla.getTarget() instanceof Zombie,'''
new = '''                helper.assertTrue(vanilla.canAttack(vanillaZombie),
                        "Vanilla natural Iron Golem cannot attack the surviving Husk probe");
                helper.assertTrue(bedrock.canAttack(bedrockZombie),
                        "Bedrock cannot attack the surviving Husk probe");
                helper.assertTrue(vanilla.canAttackType(vanillaZombie.getType()),
                        "Vanilla natural Iron Golem rejects Husk entity type");
                helper.assertTrue(bedrock.canAttackType(bedrockZombie.getType()),
                        "Bedrock canAttackType(HUSK) is false after player retaliation");
                helper.assertTrue(!vanilla.isAlliedTo(vanillaZombie),
                        "Vanilla control is unexpectedly allied to Husk probe");
                helper.assertTrue(!bedrock.isAlliedTo(bedrockZombie),
                        "Bedrock is unexpectedly allied to Husk probe after player retaliation");
                helper.assertTrue(vanillaZombie.canBeSeenByAnyone(),
                        "Vanilla Husk probe cannot be seen by anyone");
                helper.assertTrue(bedrockZombie.canBeSeenByAnyone(),
                        "Bedrock Husk probe cannot be seen by anyone");
                helper.assertTrue(vanillaZombie instanceof net.minecraft.world.entity.monster.Enemy,
                        "Vanilla Husk probe does not implement Enemy");
                helper.assertTrue(bedrockZombie instanceof net.minecraft.world.entity.monster.Enemy,
                        "Bedrock Husk probe does not implement Enemy");
                helper.assertTrue(vanilla.getSensing().hasLineOfSight(vanillaZombie),
                        "Vanilla natural Iron Golem has no line of sight to its Husk probe");
                helper.assertTrue(bedrock.getSensing().hasLineOfSight(bedrockZombie),
                        "Bedrock Sensing has no line of sight to the Husk probe after player retaliation; "
                                + "bedrockEyeY=" + bedrock.getEyeY() + ", huskEyeY=" + bedrockZombie.getEyeY()
                                + ", distance=" + bedrock.distanceTo(bedrockZombie));
                helper.assertTrue(bedrockZombie.getVisibilityPercent(bedrock) > 0.2D,
                        "Bedrock Husk visibility scaling unexpectedly shrank target range; visibility="
                                + bedrockZombie.getVisibilityPercent(bedrock));
                helper.assertTrue(vanilla.getTarget() instanceof Zombie,'''
if old not in s:
    raise SystemExit('Candidate-condition insertion marker missing')
s = s.replace(old, new, 1)
p.write_text(s)
print('Added non-invasive hostile-candidate assertions in a compact loaded layout.')