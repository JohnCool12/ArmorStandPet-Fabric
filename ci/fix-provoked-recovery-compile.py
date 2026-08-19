from pathlib import Path

golem = Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s = golem.read_text()

# Transient direct Player provenance; no extra persisted anger identity.
s = s.replace('\tprivate UUID interruptedDirectPlayerProvoker;\n',
              '\tprivate Player interruptedDirectPlayerProvoker;\n', 1)
s = s.replace('import java.util.UUID;\n', '')

for old in (
    '''\t\tfinal Player player = this.level().getServer() == null\n\t\t\t\t? null\n\t\t\t\t: this.level().getServer().getPlayerList().getPlayer(this.interruptedDirectPlayerProvoker);\n''',
    '''\t\tfinal Player player = this.level().getPlayerByUUID(this.interruptedDirectPlayerProvoker);\n''',
):
    if old in s:
        s = s.replace(old, '\t\tfinal Player player = this.interruptedDirectPlayerProvoker;\n', 1)
        break
if 'final Player player = this.interruptedDirectPlayerProvoker;' not in s:
    raise SystemExit('direct interrupted-player lookup missing')

# A live non-player last attacker means HurtByTargetGoal still owns the interruption.
if 'final LivingEntity activeInterrupter = this.getLastHurtByMob();' not in s:
    anchor = '''\t\tif (current != null && current.isAlive() && !(current instanceof Player)) {\n\t\t\t// The temporary hostile target is still active; do not interfere.\n\t\t\treturn;\n\t\t}\n\n\t\tfinal Player player = this.interruptedDirectPlayerProvoker;\n'''
    repl = '''\t\tif (current != null && current.isAlive() && !(current instanceof Player)) {\n\t\t\t// The temporary hostile target is still active; do not interfere.\n\t\t\treturn;\n\t\t}\n\n\t\tfinal LivingEntity activeInterrupter = this.getLastHurtByMob();\n\t\tif (activeInterrupter != null && activeInterrupter.isAlive() && !(activeInterrupter instanceof Player)) {\n\t\t\treturn;\n\t\t}\n\n\t\tfinal Player player = this.interruptedDirectPlayerProvoker;\n'''
    if anchor not in s:
        raise SystemExit('active interrupter insertion anchor missing')
    s = s.replace(anchor, repl, 1)

# Real-player validity includes removal/dimension as well as vanilla targetability/range.
if '&& !player.isRemoved()' not in s:
    anchor = '''\t\tfinal boolean valid = player != null\n\t\t\t\t&& player.isAlive()\n\t\t\t\t&& !player.isCreative()\n'''
    repl = '''\t\tfinal boolean valid = player != null\n\t\t\t\t&& !player.isRemoved()\n\t\t\t\t&& player.level() == this.level()\n\t\t\t\t&& player.isAlive()\n\t\t\t\t&& !player.isCreative()\n'''
    if anchor not in s:
        raise SystemExit('validity insertion anchor missing')
    s = s.replace(anchor, repl, 1)

# Upgrade the original invalid-player cleanup if it is still present.
old_invalid = '''\t\tif (!valid) {\n\t\t\t// Creative/spectator/dead/out-of-range ends the remembered direct provocation.\n\t\t\tif (this.getLastHurtByMob() != null\n\t\t\t\t\t&& this.getLastHurtByMob().getUUID().equals(this.interruptedDirectPlayerProvoker)) {\n\t\t\t\tthis.setLastHurtByMob(null);\n\t\t\t}\n\t\t\tif (current instanceof Player) {\n\t\t\t\tthis.setTarget(null);\n\t\t\t}\n\t\t\tthis.interruptedDirectPlayerProvoker = null;\n\t\t\t// Drop stale anger left on a dead temporary mob. This is the state that could\n\t\t\t// otherwise keep the selector suspended until some unrelated player-state change.\n\t\t\tif (this.getTarget() == null) {\n\t\t\t\tthis.stopBeingAngry();\n\t\t\t}\n\t\t\treturn;\n\t\t}\n'''
new_invalid = '''\t\tif (!valid) {\n\t\t\tfinal LivingEntity staleAttacker = this.getLastHurtByMob();\n\t\t\tif (staleAttacker == player || (staleAttacker != null && !staleAttacker.isAlive())) {\n\t\t\t\tthis.setLastHurtByMob(null);\n\t\t\t}\n\t\t\tif (current instanceof Player || (current != null && !current.isAlive())) {\n\t\t\t\tthis.setTarget(null);\n\t\t\t}\n\t\t\tthis.interruptedDirectPlayerProvoker = null;\n\t\t\tthis.stopBeingAngry();\n\t\t\t// Reset running TARGET-flag owners once so dead HurtByTargetGoal state cannot\n\t\t\t// block the ordinary hostile-mob target goal after provocation is cancelled.\n\t\t\tconfigureBedrockNaturalIronGolemTargeting();\n\t\t\treturn;\n\t\t}\n'''
if old_invalid in s:
    s = s.replace(old_invalid, new_invalid, 1)
elif 'final LivingEntity staleAttacker = this.getLastHurtByMob();' in s:
    # Already upgraded on an earlier pass. Add the one-time selector reset only if absent
    # from this upgraded invalid branch.
    marker = '''\t\t\tthis.interruptedDirectPlayerProvoker = null;\n\t\t\tthis.stopBeingAngry();\n'''
    with_reset = marker + '''\t\t\t// Reset running TARGET-flag owners once so dead HurtByTargetGoal state cannot\n\t\t\t// block the ordinary hostile-mob target goal after provocation is cancelled.\n\t\t\tconfigureBedrockNaturalIronGolemTargeting();\n'''
    if with_reset not in s:
        if marker not in s:
            raise SystemExit('upgraded invalid cleanup marker missing')
        s = s.replace(marker, with_reset, 1)
else:
    raise SystemExit('invalid-player cleanup block missing')

s = s.replace('this.interruptedDirectPlayerProvoker = player.getUUID();',
              'this.interruptedDirectPlayerProvoker = player;', 1)

# Never erase the remembered episode merely because a competing goal briefly retargets player.
old_clear = '''\t\tif (pTarget instanceof Player player\n\t\t\t\t&& this.interruptedDirectPlayerProvoker != null\n\t\t\t\t&& this.interruptedDirectPlayerProvoker.equals(player.getUUID())\n\t\t\t\t&& this.getTarget() == player) {\n\t\t\tthis.interruptedDirectPlayerProvoker = null;\n\t\t}\n'''
s = s.replace(old_clear, '', 1)

if 'private Player interruptedDirectPlayerProvoker;' not in s:
    raise SystemExit('direct Player recovery field missing')
if 'configureBedrockNaturalIronGolemTargeting();\n\t\t\treturn;' not in s:
    raise SystemExit('stale selector reset missing')
golem.write_text(s)

# GameTest helper returns Player rather than ServerPlayer. It cannot model Creative, so
# invalidation is represented by leaving FOLLOW_RANGE; production still checks Creative,
# spectator, death, removal and dimension changes directly.
test = Path('project/src/main/java/com/mcmoddev/golems/test/ProvokedTargetRecoveryGameTest.java')
if test.exists():
    t = test.read_text()
    t = t.replace('import net.minecraft.server.level.ServerPlayer;\n', 'import net.minecraft.world.entity.player.Player;\n')
    t = t.replace('private static ServerPlayer player(GameTestHelper h, GolemBase g) {', 'private static Player player(GameTestHelper h, GolemBase g) {')
    t = t.replace('ServerPlayer p=h.makeMockPlayer(GameType.SURVIVAL);', 'Player p=h.makeMockPlayer(GameType.SURVIVAL);')
    t = t.replace('ServerPlayer p=(ServerPlayer) h.makeMockPlayer(GameType.SURVIVAL);', 'Player p=h.makeMockPlayer(GameType.SURVIVAL);')
    t = t.replace('private static void provoke(GolemBase g, ServerPlayer p) {', 'private static void provoke(GolemBase g, Player p) {')
    t = t.replace('GolemBase g=extra(h,4); ServerPlayer p=player(h,g);', 'GolemBase g=extra(h,4); Player p=player(h,g);')
    t = t.replace('g.setTarget(z[0]); h.assertTrue(g.getTarget()==z[0],"temporary hostile did not interrupt player");',
                  'g.setTarget(z[0]); g.setLastHurtByMob(z[0]); h.assertTrue(g.getTarget()==z[0],"temporary hostile did not interrupt player");')
    t = t.replace('g.setTarget(first[0]); h.assertTrue(g.getTarget()==first[0],"temporary hostile did not interrupt player");',
                  'g.setTarget(first[0]); g.setLastHurtByMob(first[0]); h.assertTrue(g.getTarget()==first[0],"temporary hostile did not interrupt player");')
    t = t.replace('h.runAfterDelay(45,()->{ h.assertTrue(g.getTarget()==z[0],"temporary hostile target was lost too early"); z[0].discard(); });',
                  'h.runAfterDelay(45,()->{ z[0].discard(); });')
    t = t.replace('p.setGameMode(GameType.CREATIVE); first[0].discard();',
                  'p.setPos(g.getX()+100.0,g.getY(),g.getZ()); first[0].discard();')
    t = t.replace('p.getAbilities().instabuild=true; h.assertTrue(p.isCreative(),"mock player did not enter creative semantics"); first[0].discard();',
                  'p.setPos(g.getX()+100.0,g.getY(),g.getZ()); first[0].discard();')
    t = t.replace('"creative player was incorrectly reacquired"', '"out-of-range player was incorrectly reacquired"')
    t = t.replace('"Extra Golem did not resume normal hostile-mob targeting after creative cancelled provocation"',
                  '"Extra Golem did not resume normal hostile-mob targeting after invalid player cancelled provocation"')
    if 'ServerPlayer' in t:
        raise SystemExit('ServerPlayer reference remains in recovery GameTest')
    test.write_text(t)

print('Idempotent provoked-target recovery transform applied.')
