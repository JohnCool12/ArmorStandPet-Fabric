from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/test/BedrockNaturalAiGameTest.java')
s = p.read_text()

old_import = 'import net.minecraft.world.entity.EntityType;\n'
new_import = '''import net.minecraft.world.entity.EntityType;\nimport net.minecraft.world.entity.Mob;\nimport net.minecraft.world.entity.ai.goal.GoalSelector;\n'''
if old_import not in s:
    raise SystemExit('EntityType import marker missing for goal debug')
s = s.replace(old_import, new_import, 1)

old_class = '''public final class BedrockNaturalAiGameTest implements FabricGameTest {\n    @GameTest'''
new_class = '''public final class BedrockNaturalAiGameTest implements FabricGameTest {\n    private static String describeTargetGoals(final Mob mob) {\n        try {\n            final java.lang.reflect.Field f = Mob.class.getDeclaredField("targetSelector");\n            f.setAccessible(true);\n            final GoalSelector selector = (GoalSelector) f.get(mob);\n            return selector.getAvailableGoals().stream()\n                    .map(w -> w.getGoal().getClass().getSimpleName() + "[running=" + w.isRunning() + "]")\n                    .sorted()\n                    .reduce((a, b) -> a + "," + b)\n                    .orElse("<none>");\n        } catch (ReflectiveOperationException e) {\n            return "<reflection-failed:" + e.getClass().getSimpleName() + ":" + e.getMessage() + ">";\n        }\n    }\n\n    @GameTest'''
if old_class not in s:
    raise SystemExit('GameTest class marker missing for goal debug')
s = s.replace(old_class, new_class, 1)

old_failure = '''                        "Bedrock failed proactive hostile-mob reacquisition after player retaliation; currentTarget="\n                                + bedrock.getTarget() + ", lastHurt=" + bedrock.getLastHurtByMob());'''
new_failure = '''                        "Bedrock failed proactive hostile-mob reacquisition after player retaliation; currentTarget="\n                                + bedrock.getTarget() + ", lastHurt=" + bedrock.getLastHurtByMob()\n                                + ", bedrockGoals=" + describeTargetGoals(bedrock)\n                                + ", vanillaGoals=" + describeTargetGoals(vanilla));'''
if old_failure not in s:
    raise SystemExit('Final Bedrock failure marker missing for goal debug')
s = s.replace(old_failure, new_failure, 1)

p.write_text(s)
print('Added target-selector running-goal diagnostics to Bedrock AI GameTest.')
