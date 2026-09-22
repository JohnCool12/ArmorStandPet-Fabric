from pathlib import Path
p = Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s = p.read_text()
for line in (
    'import com.mcmoddev.golems.data.golem.SwimAbility;\n',
    'import com.mcmoddev.golems.entity.goal.GoToWaterGoal;\n',
    'import com.mcmoddev.golems.entity.goal.SwimUpGoal;\n',
    'import net.minecraft.world.entity.MoverType;\n',
    'import net.minecraft.world.entity.ai.control.MoveControl;\n',
    'import net.minecraft.world.entity.ai.goal.RandomSwimmingGoal;\n',
    'import net.minecraft.world.entity.ai.navigation.WaterBoundPathNavigation;\n',
):
    s = s.replace(line, '')
s = s.replace('\tprivate final WaterBoundPathNavigation waterNavigator;\n', '')
s = s.replace('\tprivate boolean swimmingUp;\n', '')
s = s.replace('\t\t// the following will be unused if swimming is not enabled\n\t\tthis.waterNavigator = new WaterBoundPathNavigation(this, world);\n', '')
s = s.replace('''\n\t//// SWIMMING ////\n\n\t@Override\n\tpublic void travel(final Vec3 vec) { super.travel(vec); }\n\n\t@Override\n\tpublic void updateSwimming() { super.updateSwimming(); }\n\n\t@Override\n\tpublic boolean isPushedByFluid() { return super.isPushedByFluid(); }\n\n\tpublic void setSwimmingUp(boolean ignored) { this.swimmingUp = false; }\n\n\tpublic boolean isSwimmingUp() { return false; }\n''', '\n')
p.write_text(s)
for dead in (
    Path('project/src/main/java/com/mcmoddev/golems/entity/goal/GoToWaterGoal.java'),
    Path('project/src/main/java/com/mcmoddev/golems/entity/goal/SwimUpGoal.java'),
):
    dead.unlink(missing_ok=True)
assert 'waterNavigator' not in s
assert 'RandomSwimmingGoal' not in s
assert 'GoToWaterGoal' not in s
assert 'SwimUpGoal' not in s
print('Removed superseded 3D-swimming implementation; V4 surface swimming remains native FloatGoal + ground navigation.')
