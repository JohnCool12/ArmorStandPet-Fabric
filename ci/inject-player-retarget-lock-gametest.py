from pathlib import Path
import json

root=Path('project')
modjson=root/'src/main/resources/fabric.mod.json'
testjava=root/'src/main/java/com/mcmoddev/golems/test/PlayerRetargetLockGameTest.java'
data=json.loads(modjson.read_text())
entries=data.setdefault('entrypoints',{}).setdefault('fabric-gametest',[])
entry='com.mcmoddev.golems.test.PlayerRetargetLockGameTest'
if entry not in entries: entries.append(entry)
modjson.write_text(json.dumps(data,indent=2)+'\n')

testjava.parent.mkdir(parents=True,exist_ok=True)
testjava.write_text(r'''package com.mcmoddev.golems.test;

import com.mcmoddev.golems.block.GolemHeadBlock;
import com.mcmoddev.golems.entity.GolemBase;
import com.mojang.authlib.GameProfile;
import net.fabricmc.fabric.api.gametest.v1.FabricGameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.server.level.ClientInformation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.monster.Zombie;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.AABB;

import java.util.List;
import java.util.UUID;

public final class PlayerRetargetLockGameTest implements FabricGameTest {
    private static ServerPlayer player(GameTestHelper helper, String name) {
        ServerPlayer p = new ServerPlayer(helper.getLevel().getServer(), helper.getLevel(),
                new GameProfile(UUID.randomUUID(), name), ClientInformation.createDefault()) {
            @Override public boolean isCreative() { return false; }
            @Override public boolean isSpectator() { return false; }
            @Override public void tick() { }
            @Override public void doTick() { }
        };
        p.gameMode.changeGameModeForPlayer(GameType.SURVIVAL);
        GameType.SURVIVAL.updatePlayerAbilities(p.getAbilities());
        p.setNoGravity(true);
        helper.getLevel().players().add(p);
        return p;
    }

    private static GolemBase construct(GameTestHelper helper, BlockPos relativeHead) {
        BlockPos head=helper.absolutePos(relativeHead);
        helper.getLevel().setBlockAndUpdate(head.below(), Blocks.OBSIDIAN.defaultBlockState());
        helper.getLevel().setBlockAndUpdate(head.below(2), Blocks.OBSIDIAN.defaultBlockState());
        helper.getLevel().setBlockAndUpdate(head.below().east(), Blocks.OBSIDIAN.defaultBlockState());
        helper.getLevel().setBlockAndUpdate(head.below().west(), Blocks.OBSIDIAN.defaultBlockState());
        helper.assertTrue(GolemHeadBlock.trySpawnGolem(null, helper.getLevel(), head), "Failed to construct Extra Golem");
        List<GolemBase> found=helper.getLevel().getEntitiesOfClass(GolemBase.class,new AABB(head).inflate(4.0D),e->e.isAlive());
        helper.assertTrue(found.size()==1,"Expected exactly one Extra Golem");
        GolemBase g=found.get(0); g.setNoGravity(true); return g;
    }

    private static Zombie zombie(GameTestHelper helper, double x, double y, double zPos) {
        Zombie mob=EntityType.ZOMBIE.create(helper.getLevel());
        helper.assertTrue(mob!=null,"Failed zombie create");
        mob.moveTo(x,y,zPos,0,0); mob.setNoGravity(true); helper.getLevel().addFreshEntity(mob); return mob;
    }

    @GameTest(template=FabricGameTest.EMPTY_STRUCTURE, timeoutTicks=100)
    public void unprovokedPlayerSetterStillRejected(GameTestHelper helper) {
        GolemBase g=construct(helper,new BlockPos(8,20,8));
        ServerPlayer p=player(helper,"UnprovokedPlayer");
        p.setPos(g.getX()+2.0D,g.getY(),g.getZ());
        g.setLastHurtByMob(null);
        g.stopBeingAngry();
        g.setTarget(p);
        helper.assertTrue(g.getTarget()==null,"Anti-shared-retaliation guard stopped rejecting an unprovoked player");
        helper.getLevel().players().remove(p); g.discard(); helper.succeed();
    }

    @GameTest(template=FabricGameTest.EMPTY_STRUCTURE, timeoutTicks=100)
    public void directProvocationStillAllowsPlayerAndAngerSurvivesLastHurtOverwrite(GameTestHelper helper) {
        GolemBase g=construct(helper,new BlockPos(8,20,24));
        ServerPlayer p=player(helper,"Provoker");
        p.setPos(g.getX()+2.0D,g.getY(),g.getZ());
        Zombie z=zombie(helper,g.getX()+3.0D,g.getY(),g.getZ());
        g.setLastHurtByMob(p);
        helper.assertTrue(g.canAttack(p),"Directly provoking player was not vanilla-attackable");
        g.setTarget(p);
        helper.assertTrue(g.getTarget()==p,"Directly provoking player could not become target");
        g.setPersistentAngerTarget(p.getUUID());
        g.setRemainingPersistentAngerTime(600);
        g.setLastHurtByMob(z);
        helper.assertTrue(g.isAngryAt(p),"Persistent player anger stopped being valid after hostile mob overwrote lastHurtByMob");
        g.setTarget(p);
        helper.assertTrue(g.getTarget()==p,"Golem could not reacquire still-valid angry player");
        helper.getLevel().players().remove(p); z.discard(); g.discard(); helper.succeed();
    }

    @GameTest(template=FabricGameTest.EMPTY_STRUCTURE, timeoutTicks=180)
    public void hostileTargetingRecoversWhenHostileOverwritesProvocation(GameTestHelper helper) {
        GolemBase g=construct(helper,new BlockPos(8,20,40));
        ServerPlayer p=player(helper,"InterruptedProvoker");
        p.setPos(g.getX()+3.0D,g.getY(),g.getZ());
        Zombie first=zombie(helper,g.getX()+2.0D,g.getY(),g.getZ()+2.0D);
        Zombie second=zombie(helper,g.getX()+4.0D,g.getY(),g.getZ()+2.0D);
        g.setLastHurtByMob(p);
        g.setTarget(p);
        for(int i=0;i<4;i++) g.tick(); // lets HurtByTargetGoal remember the player
        g.setTarget(first);            // vanilla IronGolem.doPush can do this to a hostile
        g.setLastHurtByMob(first);     // hostile also becomes the newest attacker
        for(int i=0;i<4;i++) g.tick();
        first.discard();
        if (g.getTarget()==first) g.setTarget(null);
        for(int i=0;i<60;i++) g.tick();
        LivingEntity after=g.getTarget();
        String state="target="+(after==null?"null":after.getName().getString())
                +", lastHurt="+(g.getLastHurtByMob()==null?"null":g.getLastHurtByMob().getName().getString())
                +", anger="+g.getPersistentAngerTarget()+", angerTime="+g.getRemainingPersistentAngerTime();
        helper.getLevel().players().remove(p); second.discard(); g.discard();
        helper.assertTrue(after==second,
                "Extra Golem failed to release stale player HurtBy goal and reacquire remaining hostile mob: "+state);
        helper.succeed();
    }

    @GameTest(template=FabricGameTest.EMPTY_STRUCTURE, timeoutTicks=180)
    public void validPlayerProvocationIsResumedAfterTemporaryHostileSwitch(GameTestHelper helper) {
        GolemBase g=construct(helper,new BlockPos(8,20,56));
        ServerPlayer p=player(helper,"StillProvokedPlayer");
        p.setPos(g.getX()+3.0D,g.getY(),g.getZ());
        Zombie temporary=zombie(helper,g.getX()+2.0D,g.getY(),g.getZ()+2.0D);
        g.setLastHurtByMob(p);
        g.setTarget(p);
        for(int i=0;i<4;i++) g.tick();
        // Temporary hostile switch without overwriting the original attacker memory.
        g.setTarget(temporary);
        temporary.discard();
        if (g.getTarget()==temporary) g.setTarget(null);
        for(int i=0;i<30;i++) g.tick();
        LivingEntity after=g.getTarget();
        String state="target="+(after==null?"null":after.getName().getString())
                +", lastHurt="+(g.getLastHurtByMob()==null?"null":g.getLastHurtByMob().getName().getString())
                +", anger="+g.getPersistentAngerTarget()+", angerTime="+g.getRemainingPersistentAngerTime();
        helper.getLevel().players().remove(p); g.discard();
        helper.assertTrue(after==p,"Still-valid player provocation was not resumed after temporary hostile switch: "+state);
        helper.succeed();
    }
}
''')
print('Injected stale HurtBy release, hostile recovery, and valid-player retarget GameTests.')
