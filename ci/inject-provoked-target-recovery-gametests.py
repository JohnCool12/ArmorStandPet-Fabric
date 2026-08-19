from pathlib import Path
import json
root=Path('project')
build=root/'build.gradle'; modjson=root/'src/main/resources/fabric.mod.json'
Path('/tmp/prod-build.gradle').write_text(build.read_text())
Path('/tmp/prod-fabric.mod.json').write_text(modjson.read_text())
build.write_text(build.read_text()+r'''
loom { runs { gametest { server(); name "Provoked Target Recovery"; vmArg "-Dfabric-api.gametest"; vmArg "-Dfabric-api.gametest.report-file=${project.buildDir}/junit.xml"; runDir "run/gametest" } } }
''')
data=json.loads(modjson.read_text()); data.setdefault('entrypoints',{})['fabric-gametest']=['com.mcmoddev.golems.test.ProvokedTargetRecoveryGameTest']; modjson.write_text(json.dumps(data,indent=2)+'\n')
p=root/'src/main/java/com/mcmoddev/golems/test/ProvokedTargetRecoveryGameTest.java'; p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(r'''package com.mcmoddev.golems.test;

import com.mcmoddev.golems.ExtraGolems;
import com.mcmoddev.golems.entity.GolemBase;
import net.fabricmc.fabric.api.gametest.v1.FabricGameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.monster.Zombie;
import net.minecraft.world.level.GameType;

public final class ProvokedTargetRecoveryGameTest implements FabricGameTest {
    private static GolemBase extra(GameTestHelper h, int x) {
        GolemBase g=GolemBase.create(h.getLevel(), ResourceLocation.fromNamespaceAndPath(ExtraGolems.MODID,"obsidian"));
        h.assertTrue(g!=null,"Extra golem create failed");
        g.moveTo(h.absolutePos(new BlockPos(x,2,4)),0,0);
        g.markConstructedNeutral();
        h.getLevel().addFreshEntity(g);
        return g;
    }
    private static Zombie zombie(GameTestHelper h, GolemBase g, double dz) {
        Zombie z=EntityType.ZOMBIE.create(h.getLevel());
        h.assertTrue(z!=null,"Zombie create failed");
        z.setNoAi(true); z.moveTo(g.getX()+dz,g.getY(),g.getZ(),0,0); h.getLevel().addFreshEntity(z); return z;
    }
    private static ServerPlayer player(GameTestHelper h, GolemBase g) {
        ServerPlayer p=h.makeMockPlayer(GameType.SURVIVAL); p.setPos(g.getX()+4,g.getY(),g.getZ()); return p;
    }
    private static void provoke(GolemBase g, ServerPlayer p) {
        g.setLastHurtByMob(p); g.setTarget(p); g.setPersistentAngerTarget(p.getUUID()); g.startPersistentAngerTimer();
    }

    @GameTest(template=FabricGameTest.EMPTY_STRUCTURE, timeoutTicks=160)
    public void directPlayerIsReacquiredAfterTemporaryHostileDies(GameTestHelper h) {
        GolemBase g=extra(h,4); ServerPlayer p=player(h,g); final Zombie[] z=new Zombie[1];
        h.runAfterDelay(10,()->{ provoke(g,p); h.assertTrue(g.getTarget()==p,"initial direct provocation not established"); });
        h.runAfterDelay(25,()->{ z[0]=zombie(h,g,2); g.setTarget(z[0]); h.assertTrue(g.getTarget()==z[0],"temporary hostile did not interrupt player"); });
        h.runAfterDelay(45,()->{ h.assertTrue(g.getTarget()==z[0],"temporary hostile target was lost too early"); z[0].discard(); });
        h.runAfterDelay(70,()->{
            h.assertTrue(g.getTarget()==p,"Extra Golem failed to reacquire its still-valid direct player provoker after temporary hostile died");
            h.assertTrue(g.getLastHurtByMob()==p,"direct player provenance was not restored");
            h.succeed();
        });
    }

    @GameTest(template=FabricGameTest.EMPTY_STRUCTURE, timeoutTicks=180)
    public void creativeCancelsInterruptedProvocationAndHostileTargetingRecovers(GameTestHelper h) {
        GolemBase g=extra(h,4); ServerPlayer p=player(h,g); final Zombie[] first=new Zombie[1]; final Zombie[] second=new Zombie[1];
        h.runAfterDelay(10,()->provoke(g,p));
        h.runAfterDelay(25,()->{ first[0]=zombie(h,g,2); g.setTarget(first[0]); h.assertTrue(g.getTarget()==first[0],"temporary hostile did not interrupt player"); });
        h.runAfterDelay(40,()->{ p.setGameMode(GameType.CREATIVE); first[0].discard(); });
        h.runAfterDelay(60,()->{ h.assertTrue(g.getTarget()!=p,"creative player was incorrectly reacquired"); second[0]=zombie(h,g,3); });
        h.runAfterDelay(130,()->{
            h.assertTrue(g.getTarget()==second[0],"Extra Golem did not resume normal hostile-mob targeting after creative cancelled provocation");
            h.succeed();
        });
    }
}
''')
print('Injected provoked target recovery GameTests')
