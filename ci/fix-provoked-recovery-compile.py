from pathlib import Path

golem=Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s=golem.read_text()
if 'import java.util.UUID;\n' not in s:
    anchor='import java.util.Objects;\n'
    if anchor not in s:
        raise SystemExit('Objects import anchor missing for UUID import')
    s=s.replace(anchor,anchor+'import java.util.UUID;\n',1)

old_lookup='''\t\tfinal Player player = this.level().getServer() == null\n\t\t\t\t? null\n\t\t\t\t: this.level().getServer().getPlayerList().getPlayer(this.interruptedDirectPlayerProvoker);\n'''
new_lookup='''\t\tfinal Player player = this.level().getPlayerByUUID(this.interruptedDirectPlayerProvoker);\n'''
if old_lookup in s:
    s=s.replace(old_lookup,new_lookup,1)
elif new_lookup not in s:
    raise SystemExit('player lookup anchor missing')
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
    t=t.replace('p.setGameMode(GameType.CREATIVE); first[0].discard();','p.getAbilities().instabuild=true; h.assertTrue(p.isCreative(),"mock player did not enter creative semantics"); first[0].discard();')
    if 'ServerPlayer' in t:
        raise SystemExit('ServerPlayer reference remains in recovery GameTest')
    test.write_text(t)

print('Recovery world-player lookup and mock-player compatibility fixes applied.')
