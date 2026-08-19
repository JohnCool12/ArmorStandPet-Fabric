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
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.animal.IronGolem;
import net.minecraft.world.entity.monster.Zombie;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.GameType;
public final class ProvokedInterruptionGameTest implements FabricGameTest {
 @GameTest(template=FabricGameTest.EMPTY_STRUCTURE, timeoutTicks=240)
 public void interruptedPlayerProvocationRecovers(final GameTestHelper h) {
   GolemBase e=GolemBase.create(h.getLevel(), ResourceLocation.fromNamespaceAndPath(ExtraGolems.MODID,"obsidian"));
   e.moveTo(h.absolutePos(new BlockPos(4,2,4)),0,0); e.markConstructedNeutral(); h.getLevel().addFreshEntity(e);
   IronGolem v=EntityType.IRON_GOLEM.create(h.getLevel()); h.assertTrue(v!=null,"vanilla create failed"); v.moveTo(h.absolutePos(new BlockPos(14,2,4)),0,0); v.setPlayerCreated(false); h.getLevel().addFreshEntity(v);
   Player ep=h.makeMockPlayer(GameType.SURVIVAL); ep.setPos(e.getX()+5,e.getY(),e.getZ());
   Player vp=h.makeMockPlayer(GameType.SURVIVAL); vp.setPos(v.getX()+5,v.getY(),v.getZ());
   h.runAfterDelay(20,()->{ e.setLastHurtByMob(ep); v.setLastHurtByMob(vp); });
   h.runAfterDelay(26,()->{
     h.assertTrue(e.getTarget()==ep,"extra did not initially retaliate"); h.assertTrue(v.getTarget()==vp,"vanilla did not initially retaliate");
     Zombie ez=EntityType.ZOMBIE.create(h.getLevel()), vz=EntityType.ZOMBIE.create(h.getLevel()); h.assertTrue(ez!=null&&vz!=null,"zombie create failed");
     ez.setNoAi(true); vz.setNoAi(true); ez.moveTo(e.getX()+3,e.getY(),e.getZ(),0,0); vz.moveTo(v.getX()+3,v.getY(),v.getZ(),0,0); h.getLevel().addFreshEntity(ez); h.getLevel().addFreshEntity(vz);
     e.setTarget(ez); v.setTarget(vz);
     h.runAfterDelay(8,()->{ ez.discard(); vz.discard(); });
   });
   h.runAfterDelay(55,()->{
     System.out.println("PARITY_STATE extraTarget="+e.getTarget()+" extraAngry="+e.getPersistentAngerTarget()+" extraTime="+e.getRemainingPersistentAngerTime()+" vanillaTarget="+v.getTarget()+" vanillaAngry="+v.getPersistentAngerTarget()+" vanillaTime="+v.getRemainingPersistentAngerTime());
     Zombie ez2=EntityType.ZOMBIE.create(h.getLevel()), vz2=EntityType.ZOMBIE.create(h.getLevel()); h.assertTrue(ez2!=null&&vz2!=null,"zombie2 create failed");
     ez2.setNoAi(true); vz2.setNoAi(true); ez2.moveTo(e.getX()+4,e.getY(),e.getZ(),0,0); vz2.moveTo(v.getX()+4,v.getY(),v.getZ(),0,0); h.getLevel().addFreshEntity(ez2); h.getLevel().addFreshEntity(vz2);
     h.runAfterDelay(45,()->{
       System.out.println("PARITY_FINAL extraTarget="+e.getTarget()+" extraAngry="+e.getPersistentAngerTarget()+" extraTime="+e.getRemainingPersistentAngerTime()+" vanillaTarget="+v.getTarget()+" vanillaAngry="+v.getPersistentAngerTarget()+" vanillaTime="+v.getRemainingPersistentAngerTime());
       h.assertTrue(v.getTarget()==vp || v.getTarget() instanceof Zombie,"vanilla remained target-stuck");
       h.assertTrue(e.getTarget()==ep || e.getTarget() instanceof Zombie,"extra remained target-stuck");
       h.succeed();
     });
   });
 }
}
''')
print('Injected provoked interruption GameTest')
