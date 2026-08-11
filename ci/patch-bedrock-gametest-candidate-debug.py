from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/test/BedrockNaturalAiGameTest.java')
s = p.read_text()

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
                helper.assertTrue(vanilla.getTarget() instanceof Zombie,'''
if old not in s:
    raise SystemExit('Candidate-condition insertion marker missing')
s = s.replace(old, new, 1)
p.write_text(s)
print('Added direct hostile-candidate condition assertions.')
