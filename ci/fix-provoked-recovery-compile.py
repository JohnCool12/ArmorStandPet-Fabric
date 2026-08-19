from pathlib import Path

golem=Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s=golem.read_text()
if 'import java.util.UUID;\n' not in s:
    anchor='import java.util.Objects;\n'
    if anchor not in s:
        raise SystemExit('Objects import anchor missing for UUID import')
    s=s.replace(anchor,anchor+'import java.util.UUID;\n',1)
    golem.write_text(s)

test=Path('project/src/main/java/com/mcmoddev/golems/test/ProvokedTargetRecoveryGameTest.java')
if test.exists():
    t=test.read_text()
    old='ServerPlayer p=h.makeMockPlayer(GameType.SURVIVAL);'
    new='ServerPlayer p=(ServerPlayer) h.makeMockPlayer(GameType.SURVIVAL);'
    if old in t:
        t=t.replace(old,new,1)
        test.write_text(t)
    elif new not in t:
        raise SystemExit('mock player cast anchor missing')

print('Recovery compile compatibility fixes applied.')
