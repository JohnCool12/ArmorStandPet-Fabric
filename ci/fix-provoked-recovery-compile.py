from pathlib import Path

golem=Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s=golem.read_text()

# The interrupted provoker is deliberately transient, so retain the actual Player object.
# This avoids depending on server player-list lookup and naturally invalidates death,
# disconnect, or dimension-change episodes without persisting extra state.
s=s.replace('\tprivate UUID interruptedDirectPlayerProvoker;\n',
            '\tprivate Player interruptedDirectPlayerProvoker;\n',1)
s=s.replace('import java.util.UUID;\n','')

old_lookup='''\t\tfinal Player player = this.level().getServer() == null\n\t\t\t\t? null\n\t\t\t\t: this.level().getServer().getPlayerList().getPlayer(this.interruptedDirectPlayerProvoker);\n'''
old_lookup2='''\t\tfinal Player player = this.level().getPlayerByUUID(this.interruptedDirectPlayerProvoker);\n'''
new_lookup='''\t\tfinal Player player = this.interruptedDirectPlayerProvoker;\n'''
if old_lookup in s:
    s=s.replace(old_lookup,new_lookup,1)
elif old_lookup2 in s:
    s=s.replace(old_lookup2,new_lookup,1)
elif new_lookup not in s:
    raise SystemExit('interrupted player lookup anchor missing')

# If the interrupting non-player is still the live retaliation stimulus, do not consider
# the player interruption finished merely because another target goal briefly bounced the
# current target back to the player.
anchor='''\t\tif (current != null && current.isAlive() && !(current instanceof Player)) {\n\t\t\t// The temporary hostile target is still active; do not interfere.\n\t\t\treturn;\n\t\t}\n\n\t\tfinal Player player = this.interruptedDirectPlayerProvoker;\n'''
replacement='''\t\tif (current != null && current.isAlive() && !(current instanceof Player)) {\n\t\t\t// The temporary hostile target is still active; do not interfere.\n\t\t\treturn;\n\t\t}\n\n\t\tfinal LivingEntity activeInterrupter = this.getLastHurtByMob();\n\t\tif (activeInterrupter != null && activeInterrupter.isAlive() && !(activeInterrupter instanceof Player)) {\n\t\t\t// HurtByTargetGoal may momentarily lose/reassign getTarget(), but a live non-player\n\t\t\t// last attacker means the interruption episode itself has not ended yet.\n\t\t\treturn;\n\t\t}\n\n\t\tfinal Player player = this.interruptedDirectPlayerProvoker;\n'''
if anchor in s:
    s=s.replace(anchor,replacement,1)
elif 'final LivingEntity activeInterrupter = this.getLastHurtByMob();' not in s:
    raise SystemExit('active interrupter guard anchor missing')

old_valid='''\t\tfinal boolean valid = player != null\n\t\t\t\t&& player.isAlive()\n\t\t\t\t&& !player.isCreative()\n'''
new_valid='''\t\tfinal boolean valid = player != null\n\t\t\t\t&& !player.isRemoved()\n\t\t\t\t&& player.level() == this.level()\n\t\t\t\t&& player.isAlive()\n\t\t\t\t&& !player.isCreative()\n'''
if old_valid in s:
    s=s.replace(old_valid,new_valid,1)
elif new_valid not in s:
    raise SystemExit('valid interrupted player anchor missing')

old_invalid='''\t\tif (!valid) {\n\t\t\t// Creative/spectator/dead/out-of-range ends the remembered direct provocation.\n\t\t\tif (this.getLastHurtByMob() != null\n\t\t\t\t\t&& this.getLastHurtByMob().getUUID().equals(this.interruptedDirectPlayerProvoker)) {\n\t\t\t\tthis.setLastHurtByMob(null);\n\t\t\t}\n\t\t\tif (current instanceof Player) {\n\t\t\t\tthis.setTarget(null);\n\t\t\t}\n\t\t\tthis.interruptedDirectPlayerProvoker = null;\n\t\t\t// Drop stale anger left on a dead temporary mob. This is the state that could\n\t\t\t// otherwise keep the selector suspended until some unrelated player-state change.\n\t\t\tif (this.getTarget() == null) {\n\t\t\t\tthis.stopBeingAngry();\n\t\t\t}\n\t\t\treturn;\n\t\t}\n'''
new_invalid='''\t\tif (!valid) {\n\t\t\t// Creative/spectator/dead/out-of-range ends the remembered direct provocation.\n\t\t\t// Also scrub the dead temporary hostile from both target and hurt provenance so\n\t\t\t// the normal hostile selector cannot remain suspended on stale combat state.\n\t\t\tfinal LivingEntity staleAttacker = this.getLastHurtByMob();\n\t\t\tif (staleAttacker == player || (staleAttacker != null && !staleAttacker.isAlive())) {\n\t\t\t\tthis.setLastHurtByMob(null);\n\t\t\t}\n\t\t\tif (current instanceof Player || (current != null && !current.isAlive())) {\n\t\t\t\tthis.setTarget(null);\n\t\t\t}\n\t\t\tthis.interruptedDirectPlayerProvoker = null;\n\t\t\tthis.stopBeingAngry();\n\t\t\treturn;\n\t\t}\n'''
if old_invalid in s:
    s=s.replace(old_invalid,new_invalid,1)
elif 'final LivingEntity staleAttacker = this.getLastHurtByMob();' not in s:
    raise SystemExit('invalid cleanup block anchor missing')

s=s.replace('this.interruptedDirectPlayerProvoker = player.getUUID();',
            'this.interruptedDirectPlayerProvoker = player;',1)

# Never clear the remembered interruption merely because another goal transiently points
# back at the player. The recovery method itself clears it only after the non-player
# interruption is actually over and the player has been intentionally restored.
old_clear='''\t\tif (pTarget instanceof Player player\n\t\t\t\t&& this.interruptedDirectPlayerProvoker != null\n\t\t\t\t&& this.interruptedDirectPlayerProvoker.equals(player.getUUID())\n\t\t\t\t&& this.getTarget() == player) {\n\t\t\tthis.interruptedDirectPlayerProvoker = null;\n\t\t}\n'''
if old_clear in s:
    s=s.replace(old_clear,'',1)

if 'UUID interruptedDirectPlayerProvoker' in s or 'PlayerList().getPlayer(this.interruptedDirectPlayerProvoker)' in s:
    raise SystemExit('obsolete UUID recovery state remains')
golem.write_text(s)

test=Path('project/src/main/java/com/mcmoddev/golems/test/ProvokedTargetRecoveryGameTest.java')
if test.exists():
    t=test.read_text()
    t=t.replace('import net.minecraft.server.level.ServerPlayer;\n','import net.minecraft.world.entity.player.Player;\n')
    t=t.replace('private static ServerPlayer player(GameTestHelper h, GolemBase g) {','private static Player player(GameTestHelper h, GolemBase g) {')
    t=t.replace('ServerPlayer p=h.makeMockPlayer(GameType.SURVIVAL);','Player p=h.makeMockPlayer(GameType.SURVIVAL);')
    t=t.replace('ServerPlayer p=(ServerPlayer) h.makeMockPlayer(GameType.SURVIVAL);','Player p=h.makeMockPlayer(GameType.SURVIVAL);')
    t=t.replace('private static void provoke(GolemBase g, ServerPlayer p) {','private static void provoke(GolemBase g, Player p) {')
    t=t.replace('GolemBase g=extra(h,4); ServerPlayer p=player(h,g);','GolemBase g=extra(h,4); Player p=player(h,g);')

    t=t.replace('g.setTarget(z[0]); h.assertTrue(g.getTarget()==z[0],"temporary hostile did not interrupt player");',
                'g.setTarget(z[0]); g.setLastHurtByMob(z[0]); h.assertTrue(g.getTarget()==z[0],"temporary hostile did not interrupt player");')
    t=t.replace('g.setTarget(first[0]); h.assertTrue(g.getTarget()==first[0],"temporary hostile did not interrupt player");',
                'g.setTarget(first[0]); g.setLastHurtByMob(first[0]); h.assertTrue(g.getTarget()==first[0],"temporary hostile did not interrupt player");')
    t=t.replace('h.runAfterDelay(45,()->{ h.assertTrue(g.getTarget()==z[0],"temporary hostile target was lost too early"); z[0].discard(); });',
                'h.runAfterDelay(45,()->{ z[0].discard(); });')
    t=t.replace('p.setGameMode(GameType.CREATIVE); first[0].discard();',
                'p.setPos(g.getX()+100.0,g.getY(),g.getZ()); first[0].discard();')
    t=t.replace('p.getAbilities().instabuild=true; h.assertTrue(p.isCreative(),"mock player did not enter creative semantics"); first[0].discard();',
                'p.setPos(g.getX()+100.0,g.getY(),g.getZ()); first[0].discard();')
    t=t.replace('"creative player was incorrectly reacquired"','"out-of-range player was incorrectly reacquired"')
    t=t.replace('"Extra Golem did not resume normal hostile-mob targeting after creative cancelled provocation"',
                '"Extra Golem did not resume normal hostile-mob targeting after invalid player cancelled provocation"')

    if 'ServerPlayer' in t:
        raise SystemExit('ServerPlayer reference remains in recovery GameTest')
    test.write_text(t)

print('Recovery race fix, stale-hostile cleanup, and realistic GameTest compatibility applied.')
