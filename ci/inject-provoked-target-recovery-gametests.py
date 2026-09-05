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

golem_path=root/'src/main/java/com/mcmoddev/golems/entity/GolemBase.java'
gs=golem_path.read_text()
if 'debugProvokedRecoveryTargetGoals' not in gs:
    idx=gs.rfind('\n}')
    if idx < 0: raise SystemExit('GolemBase final brace not found')
    debug=r'''

	public String debugProvokedRecoveryTargetGoals() {
		return this.targetSelector.getAvailableGoals().stream()
				.map(w -> w.getGoal().getClass().getSimpleName() + ":" + w.isRunning())
				.collect(java.util.stream.Collectors.joining(","));
	}

	public String debugProvokedRecoveryTargetGoalCanUse() {
		return this.targetSelector.getAvailableGoals().stream()
				.map(w -> {
					String can;
					try { can = Boolean.toString(w.getGoal().canUse()); }
					catch (Throwable t) { can = "ERR-" + t.getClass().getSimpleName(); }
					return w.getGoal().getClass().getSimpleName() + "[running=" + w.isRunning() + ",canUse=" + can + "]";
				})
				.collect(java.util.stream.Collectors.joining(","));
	}

	public String debugProvokedRecoverySelectorInternals() {
		try {
			StringBuilder out = new StringBuilder();
			for (java.lang.reflect.Field f : net.minecraft.world.entity.ai.goal.GoalSelector.class.getDeclaredFields()) {
				f.setAccessible(true);
				Object v = f.get(this.targetSelector);
				if (v instanceof java.util.Map<?, ?> map) {
					if (out.length() > 0) out.append('|');
					out.append(f.getName()).append('=').append(map);
				} else if (v instanceof java.util.Set<?> set && f.getName().toLowerCase().contains("disable")) {
					if (out.length() > 0) out.append('|');
					out.append(f.getName()).append('=').append(set);
				}
			}
			return out.toString();
		} catch (Throwable t) {
			return "ERR-" + t.getClass().getSimpleName() + ":" + t.getMessage();
		}
	}
'''
    gs=gs[:idx]+debug+gs[idx:]
    golem_path.write_text(gs)

p=root/'src/main/java/com/mcmoddev/golems/test/ProvokedTargetRecoveryGameTest.java'; p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(r'''package com.mcmoddev.golems.test;

import com.mcmoddev.golems.ExtraGolems;
import com.mcmoddev.golems.entity.GolemBase;
import net.fabricmc.fabric.api.gametest.v1.FabricGameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.monster.Zombie;
import net.minecraft.world.entity.player.Player;
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
    private static Zombie zombie(GameTestHelper h, GolemBase g, double dx) {
        Zombie z=EntityType.ZOMBIE.create(h.getLevel());
        h.assertTrue(z!=null,"Zombie create failed");
        z.setNoAi(true); z.moveTo(g.getX()+dx,g.getY(),g.getZ(),0,0); h.getLevel().addFreshEntity(z); return z;
    }
    private static Player player(GameTestHelper h, GolemBase g) {
        Player p=h.makeMockPlayer(GameType.SURVIVAL); p.setPos(g.getX()+4,g.getY(),g.getZ()); return p;
    }
    private static void provoke(GolemBase g, Player p) {
        g.setLastHurtByMob(p); g.setTarget(p); g.setPersistentAngerTarget(p.getUUID()); g.startPersistentAngerTimer();
    }
    private static boolean acquiredOrKilled(GolemBase g, Zombie z) { return g.getTarget()==z || z.isRemoved() || !z.isAlive(); }
    private static String ent(LivingEntity e) { return e==null ? "null" : e.getType().toString()+"/"+e.getUUID()+" alive="+e.isAlive()+" removed="+e.isRemoved(); }
    private static void trace(String label, GolemBase g, Player p, Zombie z) {
        System.out.println(label+" target="+ent(g.getTarget())+" lastHurt="+ent(g.getLastHurtByMob())
            +" anger="+g.getPersistentAngerTarget()+" angerTime="+g.getRemainingPersistentAngerTime()
            +" followRange="+g.getAttributeValue(Attributes.FOLLOW_RANGE)+" playerDist2="+g.distanceToSqr(p)
            +" zDist2="+(z==null?-1.0:g.distanceToSqr(z))+" z="+ent(z)
            +" zCanAttack="+(z!=null&&g.canAttack(z))+" zCanAttackType="+(z!=null&&g.canAttackType(z.getType()))
            +" zAllied="+(z!=null&&g.isAlliedTo(z))+" goals=["+g.debugProvokedRecoveryTargetGoals()+"]");
    }
    private static void debugFailure(GolemBase g) {
        System.out.println("REC_FAIL_CANUSE "+g.debugProvokedRecoveryTargetGoalCanUse());
        System.out.println("REC_FAIL_INTERNALS "+g.debugProvokedRecoverySelectorInternals());
    }

    @GameTest(template=FabricGameTest.EMPTY_STRUCTURE, timeoutTicks=160)
    public void directPlayerIsReacquiredAfterTemporaryHostileDies(GameTestHelper h) {
        GolemBase g=extra(h,4); Player p=player(h,g); final Zombie[] z=new Zombie[1];
        h.runAfterDelay(10,()->{ provoke(g,p); h.assertTrue(g.getTarget()==p,"initial direct provocation not established"); });
        h.runAfterDelay(25,()->{ z[0]=zombie(h,g,2); g.setTarget(z[0]); g.setLastHurtByMob(z[0]); h.assertTrue(g.getTarget()==z[0],"temporary hostile did not interrupt player"); });
        h.runAfterDelay(45,()->z[0].discard());
        h.runAfterDelay(70,()->{ h.assertTrue(g.getTarget()==p,"Extra Golem failed to reacquire its still-valid direct player provoker after temporary hostile died"); h.assertTrue(g.getLastHurtByMob()==p,"direct player provenance was not restored"); h.succeed(); });
    }

    @GameTest(template=FabricGameTest.EMPTY_STRUCTURE, timeoutTicks=280)
    public void creativeCancelsInterruptedProvocationAndHostileTargetingRecovers(GameTestHelper h) {
        GolemBase g=extra(h,4); Player p=player(h,g); final Zombie[] first=new Zombie[1]; final Zombie[] second=new Zombie[1]; final Zombie[] third=new Zombie[1];
        h.runAfterDelay(10,()->provoke(g,p));
        h.runAfterDelay(25,()->{ first[0]=zombie(h,g,2); g.setTarget(first[0]); g.setLastHurtByMob(first[0]); h.assertTrue(g.getTarget()==first[0],"temporary hostile did not interrupt player"); });
        h.runAfterDelay(40,()->{ p.setPos(g.getX()+100.0,g.getY(),g.getZ()); first[0].discard(); trace("REC40_AFTER_CANCEL",g,p,first[0]); });
        h.runAfterDelay(60,()->{ h.assertTrue(g.getTarget()!=p,"invalid player was incorrectly reacquired"); second[0]=zombie(h,g,4); trace("REC60_SPAWN_SECOND",g,p,second[0]); });
        // NearestAttackableTargetGoal intentionally uses randomized acquisition attempts.
        // Give it a long window like the established Bedrock regression; if the golem
        // acquired and killed the hostile during the window, that is also success.
        h.runAfterDelay(130,()->{
            trace("REC130_SECOND",g,p,second[0]);
            if (!acquiredOrKilled(g,second[0])) debugFailure(g);
            h.assertTrue(acquiredOrKilled(g,second[0]),"Extra Golem never acquired the first hostile after player provocation was cancelled");
            if (!second[0].isRemoved()) second[0].discard();
        });
        h.runAfterDelay(145,()->{ third[0]=zombie(h,g,4); trace("REC145_SPAWN_THIRD",g,p,third[0]); });
        h.runAfterDelay(220,()->{
            trace("REC220_THIRD",g,p,third[0]);
            if (!acquiredOrKilled(g,third[0])) debugFailure(g);
            h.assertTrue(acquiredOrKilled(g,third[0]),"Extra Golem became permanently stuck instead of acquiring the next hostile");
            h.succeed();
        });
    }
}
''')
print('Injected robust-window consecutive provoked-target recovery GameTests')
