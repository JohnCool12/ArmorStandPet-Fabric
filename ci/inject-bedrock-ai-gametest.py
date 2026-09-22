from pathlib import Path
import json

root = Path('project')
build = root / 'build.gradle'
modjson = root / 'src/main/resources/fabric.mod.json'
testjava = root / 'src/main/java/com/mcmoddev/golems/test/BedrockNaturalAiGameTest.java'

(root / 'build.gradle.gametest-backup').write_text(build.read_text())
(root / 'src/main/resources/fabric.mod.json.gametest-backup').write_text(modjson.read_text())

build.write_text(build.read_text() + r'''

// Temporary CI-only server GameTest run. Removed before the production JAR build.
loom {
    runs {
        gametest {
            server()
            name "Bedrock AI Game Test"
            vmArg "-Dfabric-api.gametest"
            vmArg "-Dfabric-api.gametest.report-file=${project.buildDir}/junit.xml"
            runDir "run/gametest"
        }
    }
}
''')

data = json.loads(modjson.read_text())
data.setdefault('entrypoints', {})['fabric-gametest'] = [
    'com.mcmoddev.golems.test.BedrockNaturalAiGameTest'
]
modjson.write_text(json.dumps(data, indent=2) + '\n')

testjava.parent.mkdir(parents=True, exist_ok=True)
testjava.write_text(r'''package com.mcmoddev.golems.test;

import com.mcmoddev.golems.ExtraGolems;
import com.mcmoddev.golems.entity.GolemBase;
import net.fabricmc.fabric.api.gametest.v1.FabricGameTest;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.animal.IronGolem;
import net.minecraft.world.entity.monster.Zombie;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.GameType;

/** CI-only regression test. This class is deleted before packaging the production JAR. */
public final class BedrockNaturalAiGameTest implements FabricGameTest {
    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 360)
    public void bedrockRecoversHostileTargetAfterPlayerRetaliation(final GameTestHelper helper) {
        final GolemBase bedrock = GolemBase.create(helper.getLevel(),
                ResourceLocation.fromNamespaceAndPath(ExtraGolems.MODID, "bedrock"));
        bedrock.moveTo(helper.absolutePos(new net.minecraft.core.BlockPos(4, 2, 4)), 0.0F, 0.0F);
        bedrock.markConstructedNeutral();
        helper.getLevel().addFreshEntity(bedrock);

        final IronGolem vanilla = EntityType.IRON_GOLEM.create(helper.getLevel());
        helper.assertTrue(vanilla != null, "Failed to create vanilla Iron Golem");
        vanilla.moveTo(helper.absolutePos(new net.minecraft.core.BlockPos(10, 2, 4)), 0.0F, 0.0F);
        vanilla.setPlayerCreated(false);
        helper.getLevel().addFreshEntity(vanilla);

        final Player bedrockAttacker = helper.makeMockPlayer(GameType.SURVIVAL);
        bedrockAttacker.setPos(bedrock.getX() + 6.0D, bedrock.getY(), bedrock.getZ());
        final Player vanillaAttacker = helper.makeMockPlayer(GameType.SURVIVAL);
        vanillaAttacker.setPos(vanilla.getX() + 6.0D, vanilla.getY(), vanilla.getZ());

        helper.runAfterDelay(20, () -> {
            helper.assertTrue(bedrock.tickCount > 0,
                    "Bedrock entity is not ticking in the GameTest chunk");
            helper.assertTrue(vanilla.tickCount > 0,
                    "Vanilla Iron Golem entity is not ticking in the GameTest chunk");
            helper.assertTrue(bedrockAttacker.isAlive() && vanillaAttacker.isAlive(),
                    "Mock survival player is not a live target");
            helper.assertTrue(!bedrock.isPlayerCreated(),
                    "Bedrock Golem incorrectly entered player-created/custom-neutral semantics");

            final boolean bedrockType = bedrock.canAttackType(EntityType.PLAYER);
            final boolean vanillaType = vanilla.canAttackType(EntityType.PLAYER);
            final boolean bedrockAttack = bedrock.canAttack(bedrockAttacker);
            final boolean vanillaAttack = vanilla.canAttack(vanillaAttacker);
            helper.assertTrue(vanillaType,
                    "Vanilla natural Iron Golem baseline rejects EntityType.PLAYER");
            helper.assertTrue(vanillaAttack,
                    "Vanilla natural Iron Golem baseline rejects the mock survival player");
            helper.assertTrue(bedrockType,
                    "Bedrock canAttackType(PLAYER) is false while PlayerCreated=false");
            helper.assertTrue(bedrockAttack,
                    "Bedrock canAttack(player) differs from vanilla natural semantics");

            // Verify Bedrock's invulnerability bridge independently: a real attempted hit
            // must create the same last-attacker stimulus while leaving health unchanged.
            final float bedrockHealth = bedrock.getHealth();
            final int oldBedrockTimestamp = bedrock.getLastHurtByMobTimestamp();
            bedrock.hurt(helper.getLevel().damageSources().playerAttack(bedrockAttacker), 1.0F);
            helper.assertTrue(bedrock.getHealth() == bedrockHealth,
                    "Bedrock Golem took actual damage during provocation test");
            helper.assertTrue(bedrock.getLastHurtByMob() == bedrockAttacker,
                    "Bedrock attempted-hit bridge did not set lastHurtByMob");
            helper.assertTrue(bedrock.getLastHurtByMobTimestamp() != oldBedrockTimestamp,
                    "Bedrock attempted-hit bridge did not advance the hurt timestamp; tickCount="
                            + bedrock.tickCount + ", timestamp=" + bedrock.getLastHurtByMobTimestamp());

            // Give the vanilla control the exact same retaliation stimulus. From this point
            // forward the target-goal comparison is apples-to-apples.
            vanilla.setLastHurtByMob(vanillaAttacker);
        });

        // Check retaliation almost immediately, before Bedrock's stronger attack can kill
        // the mock player and invalidate the disengagement scenario.
        helper.runAfterDelay(23, () -> {
            helper.assertTrue(vanillaAttacker.isAlive(),
                    "Vanilla mock attacker died before the retaliation checkpoint");
            helper.assertTrue(bedrockAttacker.isAlive(),
                    "Bedrock mock attacker died before the retaliation checkpoint");
            helper.assertTrue(vanilla.getTarget() == vanillaAttacker,
                    "Vanilla target stack did not respond to setLastHurtByMob stimulus; "
                            + "tickCount=" + vanilla.tickCount
                            + ", timestamp=" + vanilla.getLastHurtByMobTimestamp()
                            + ", canAttack=" + vanilla.canAttack(vanillaAttacker));
            helper.assertTrue(bedrock.getTarget() == bedrockAttacker,
                    "Bedrock target stack did not match vanilla retaliation; "
                            + "lastHurtMatches=" + (bedrock.getLastHurtByMob() == bedrockAttacker)
                            + ", timestamp=" + bedrock.getLastHurtByMobTimestamp()
                            + ", canAttack=" + bedrock.canAttack(bedrockAttacker)
                            + ", canAttackType=" + bedrock.canAttackType(EntityType.PLAYER)
                            + ", playerCreated=" + bedrock.isPlayerCreated());

            // Reproduce the user's successful escape: move each provoking player far beyond
            // the golem's normal targeting range before either can be killed.
            bedrockAttacker.setPos(bedrock.getX() + 128.0D, bedrock.getY(), bedrock.getZ());
            vanillaAttacker.setPos(vanilla.getX() + 128.0D, vanilla.getY(), vanilla.getZ());
        });

        helper.runAfterDelay(175, () -> {
            helper.assertTrue(vanilla.getTarget() != vanillaAttacker,
                    "Vanilla baseline retained the remote player target");
            helper.assertTrue(bedrock.getTarget() != bedrockAttacker,
                    "Bedrock retained the remote player target after vanilla would disengage");

            final Zombie bedrockZombie = EntityType.ZOMBIE.create(helper.getLevel());
            final Zombie vanillaZombie = EntityType.ZOMBIE.create(helper.getLevel());
            helper.assertTrue(bedrockZombie != null && vanillaZombie != null,
                    "Failed to create hostile-mob probes");
            bedrockZombie.setNoAi(true);
            vanillaZombie.setNoAi(true);
            bedrockZombie.moveTo(bedrock.getX() + 4.0D, bedrock.getY(), bedrock.getZ(), 0.0F, 0.0F);
            vanillaZombie.moveTo(vanilla.getX() + 4.0D, vanilla.getY(), vanilla.getZ(), 0.0F, 0.0F);
            helper.getLevel().addFreshEntity(bedrockZombie);
            helper.getLevel().addFreshEntity(vanillaZombie);

            // The zombies cannot attack, so success requires proactive hostile-mob target
            // acquisition rather than HurtBy retaliation. Either zombie is acceptable because
            // both are valid hostile targets in the shared test area.
            helper.succeedWhen(() -> {
                helper.assertTrue(vanilla.getTarget() instanceof Zombie,
                        "Vanilla baseline has not proactively acquired a hostile mob yet");
                helper.assertTrue(bedrock.getTarget() instanceof Zombie,
                        "Bedrock failed proactive hostile-mob reacquisition after player retaliation; currentTarget="
                                + bedrock.getTarget() + ", lastHurt=" + bedrock.getLastHurtByMob());
            });
        });
    }
}
''')

print('Injected escape-safe Bedrock-vs-vanilla AI GameTest harness.')
