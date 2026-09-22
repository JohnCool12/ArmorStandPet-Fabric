from pathlib import Path
import json
root=Path('project')
build=root/'build.gradle'; modjson=root/'src/main/resources/fabric.mod.json'
(root/'build.gradle.gametest-backup').write_text(build.read_text())
(root/'src/main/resources/fabric.mod.json.gametest-backup').write_text(modjson.read_text())
build.write_text(build.read_text()+r'''
loom { runs { gametest { server(); name "Provoked Interruption Parity"; vmArg "-Dfabric-api.gametest"; vmArg "-Dfabric-api.gametest.report-file=${project.buildDir}/junit.xml"; runDir "run/gametest" } } }
''')
data=json.loads(modjson.read_text()); data.setdefault('entrypoints',{})['fabric-gametest']=['com.mcmoddev.golems.test.ProvokedInterruptionGameTest']; modjson.write_text(json.dumps(data,indent=2)+'\n')
p=root/'src/main/java/com/mcmoddev/golems/test/ProvokedInterruptionGameTest.java'; p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(r'''package com.mcmoddev.golems.test;
import com.mcmoddev.golems.ExtraGolems;
import com.mcmoddev.golems.entity.GolemBase;
import net.fabricmc.fabric.api.gametest.v1.FabricGameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.*;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.*;
import net.minecraft.world.entity.animal.IronGolem;
import net.minecraft.world.entity.monster.Zombie;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.GameType;
import java.lang.reflect.Method;
public final class ProvokedInterruptionGameTest implements FabricGameTest {
 private static void state(String label, IronGolem g) {
   System.out.println(label+" target="+(g.getTarget()==null?"null":g.getTarget().getType()+"/"+g.getTarget().getUUID())+
     " lastHurt="+(g.getLastHurtByMob()==null?"null":g.getLastHurtByMob().getType()+"/"+g.getLastHurtByMob().getUUID())+
     " angry="+g.getPersistentAngerTarget()+" time="+g.getRemainingPersistentAngerTime()+" playerCreated="+g.isPlayerCreated()+" tags="+g.getTags());
 }
 private static void forceVanillaPush(IronGolem g, Entity e) {
   try { Method m=IronGolem.class.getDeclaredMethod("doPush", Entity.class); m.setAccessible(true); for(int i=0;i<200 && g.getTarget()!=e;i++) m.invoke(g,e); }
   catch(Exception x){ throw new RuntimeException(x); }
 }
 @GameTest(template=FabricGameTest.EMPTY_STRUCTURE, timeoutTicks=220)
 public void interruptedPlayerProvocationRecovers(final GameTestHelper h) {
   GolemBase e=GolemBase.create(h.getLevel(), ResourceLocation.fromNamespaceAndPath(ExtraGolems.MODID,"obsidian"));
   e.moveTo(h.absolutePos(new BlockPos(4,2,4)),0,0); e.markConstructedNeutral(); h.getLevel().addFreshEntity(e);
   IronGolem v=EntityType.IRON_GOLEM.create(h.getLevel()); h.assertTrue(v!=null,"vanilla create failed"); v.moveTo(h.absolutePos(new BlockPos(14,2,4)),0,0); v.setPlayerCreated(false); h.getLevel().addFreshEntity(v);
   Player ep=h.makeMockPlayer(GameType.SURVIVAL); ep.setPos(e.getX()+4,e.getY(),e.getZ());
   Player vp=h.makeMockPlayer(GameType.SURVIVAL); vp.setPos(v.getX()+4,v.getY(),v.getZ());
   final Zombie[] firstE=new Zombie[1], firstV=new Zombie[1], secondE=new Zombie[1], secondV=new Zombie[1];
   h.runAfterDelay(10,()->{ e.setLastHurtByMob(ep); v.setLastHurtByMob(vp); e.setTarget(ep); v.setTarget(vp); e.setPersistentAngerTarget(ep.getUUID()); v.setPersistentAngerTarget(vp.getUUID()); e.startPersistentAngerTimer(); v.startPersistentAngerTimer(); state("P10_EXTRA",e); state("P10_VANILLA",v); });
   h.runAfterDelay(30,()->{
     state("P30_EXTRA_BEFORE",e); state("P30_VANILLA_BEFORE",v);
     firstE[0]=EntityType.ZOMBIE.create(h.getLevel()); firstV[0]=EntityType.ZOMBIE.create(h.getLevel()); h.assertTrue(firstE[0]!=null&&firstV[0]!=null,"first zombie create failed");
     firstE[0].setNoAi(true); firstV[0].setNoAi(true); firstE[0].moveTo(e.getX()+2,e.getY(),e.getZ(),0,0); firstV[0].moveTo(v.getX()+2,v.getY(),v.getZ(),0,0); h.getLevel().addFreshEntity(firstE[0]); h.getLevel().addFreshEntity(firstV[0]);
     forceVanillaPush(e,firstE[0]); forceVanillaPush(v,firstV[0]); state("P30_EXTRA_AFTER_PUSH",e); state("P30_VANILLA_AFTER_PUSH",v);
   });
   h.runAfterDelay(42,()->{ state("P42_EXTRA",e); state("P42_VANILLA",v); firstE[0].discard(); firstV[0].discard(); });
   h.runAfterDelay(65,()->{ state("P65_EXTRA_POST_DEATH",e); state("P65_VANILLA_POST_DEATH",v);
     secondE[0]=EntityType.ZOMBIE.create(h.getLevel()); secondV[0]=EntityType.ZOMBIE.create(h.getLevel()); h.assertTrue(secondE[0]!=null&&secondV[0]!=null,"second zombie create failed");
     secondE[0].setNoAi(true); secondV[0].setNoAi(true); secondE[0].moveTo(e.getX()+3,e.getY(),e.getZ(),0,0); secondV[0].moveTo(v.getX()+3,v.getY(),v.getZ(),0,0); h.getLevel().addFreshEntity(secondE[0]); h.getLevel().addFreshEntity(secondV[0]);
   });
   h.runAfterDelay(130,()->{ state("P130_EXTRA_FINAL",e); state("P130_VANILLA_FINAL",v);
     h.assertTrue(e.getTarget()==ep || e.getTarget()==secondE[0],"extra remained target-deadlocked after interruption");
     h.assertTrue(v.getTarget()==vp || v.getTarget()==secondV[0],"vanilla remained target-deadlocked after interruption");
     h.succeed();
   });
 }
}
''')
print('Injected corrected provoked interruption GameTest')
