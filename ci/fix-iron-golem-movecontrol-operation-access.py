from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/mixin/IronGolemMoveControlMixin.java')
s = p.read_text()

s = s.replace('    @Shadow protected MoveControl.Operation operation;\n', '')
s = s.replace('    @Unique private boolean extraGolems$wasMovingTo;\n', '')
s = s.replace('        this.extraGolems$wasMovingTo = this.operation == MoveControl.Operation.MOVE_TO;\n', '')
s = s.replace('                || !this.extraGolems$wasMovingTo\n', '')

if 'MoveControl.Operation' in s or 'extraGolems$wasMovingTo' in s:
    raise SystemExit('failed to remove protected MoveControl.Operation dependency')

p.write_text(s)
print('Removed unnecessary protected MoveControl.Operation dependency from down-step yaw guard.')
