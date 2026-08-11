from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/test/BedrockNaturalAiGameTest.java')
s = p.read_text()

old_import = 'import net.minecraft.world.entity.EntityType;\n'
new_import = 'import net.minecraft.world.Difficulty;\nimport net.minecraft.world.entity.EntityType;\n'
if old_import not in s:
    raise SystemExit('EntityType import marker missing')
s = s.replace(old_import, new_import, 1)

old_method = '''    public void bedrockRecoversHostileTargetAfterPlayerRetaliation(final GameTestHelper helper) {\n        final GolemBase bedrock ='''
new_method = '''    public void bedrockRecoversHostileTargetAfterPlayerRetaliation(final GameTestHelper helper) {\n        // Make hostile-mob lifecycle deterministic. GameTest worlds may otherwise inherit\n        // a difficulty where Zombies are immediately discarded, which invalidates the\n        // vanilla Iron Golem control before Bedrock can even be compared.\n        helper.getLevel().getServer().setDifficulty(Difficulty.NORMAL, true);\n\n        final GolemBase bedrock ='''
if old_method not in s:
    raise SystemExit('GameTest method marker missing')
s = s.replace(old_method, new_method, 1)

old_zombies = '''            helper.assertTrue(bedrockZombie != null && vanillaZombie != null,\n                    "Failed to create hostile-mob probes");\n            bedrockZombie.setNoAi(true);\n            vanillaZombie.setNoAi(true);'''
new_zombies = '''            helper.assertTrue(bedrockZombie != null && vanillaZombie != null,\n                    "Failed to create hostile-mob probes");\n            bedrockZombie.setPersistenceRequired();\n            vanillaZombie.setPersistenceRequired();\n            bedrockZombie.setNoAi(true);\n            vanillaZombie.setNoAi(true);'''
if old_zombies not in s:
    raise SystemExit('Zombie probe marker missing')
s = s.replace(old_zombies, new_zombies, 1)

old_success = '''            helper.succeedWhen(() -> {\n                helper.assertTrue(vanilla.getTarget() instanceof Zombie,\n                        "Vanilla baseline has not proactively acquired a hostile mob yet");\n                helper.assertTrue(bedrock.getTarget() instanceof Zombie,\n                        "Bedrock failed proactive hostile-mob reacquisition after player retaliation; currentTarget="\n                                + bedrock.getTarget() + ", lastHurt=" + bedrock.getLastHurtByMob());\n            });'''
new_success = '''            helper.succeedWhen(() -> {\n                helper.assertTrue(vanillaZombie.isAlive() && !vanillaZombie.isRemoved(),\n                        "Vanilla hostile-mob probe disappeared before it could be targeted; difficulty="\n                                + helper.getLevel().getDifficulty());\n                helper.assertTrue(bedrockZombie.isAlive() && !bedrockZombie.isRemoved(),\n                        "Bedrock hostile-mob probe disappeared before it could be targeted; difficulty="\n                                + helper.getLevel().getDifficulty());\n                helper.assertTrue(vanilla.canAttack(vanillaZombie),\n                        "Vanilla natural Iron Golem cannot attack the surviving Zombie probe");\n                helper.assertTrue(bedrock.canAttack(bedrockZombie),\n                        "Bedrock cannot attack the surviving Zombie probe");\n                helper.assertTrue(vanilla.getTarget() instanceof Zombie,\n                        "Vanilla baseline has not proactively acquired a hostile mob yet; difficulty="\n                                + helper.getLevel().getDifficulty());\n                helper.assertTrue(bedrock.getTarget() instanceof Zombie,\n                        "Bedrock failed proactive hostile-mob reacquisition after player retaliation; currentTarget="\n                                + bedrock.getTarget() + ", lastHurt=" + bedrock.getLastHurtByMob());\n            });'''
if old_success not in s:
    raise SystemExit('succeedWhen marker missing')
s = s.replace(old_success, new_success, 1)

p.write_text(s)
print('Patched Bedrock AI GameTest to NORMAL difficulty with persistent hostile probes.')
