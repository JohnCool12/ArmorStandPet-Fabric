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
    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 320)
    public void bedrockRecoversHostileTargetAfterPlayerRetaliation(final GameTestHelper helper) {
        final GolemBase bedrock = GolemBase.create(helper.getLevel(),
                ResourceLocation.fromNamespaceAndPath(ExtraGolems.MODID, "bedrock"));
        bedrock.moveTo(helper.absolutePos(new net.minecraft.core.BlockPos(4, 2, 4)), 0.0F, 0.0F);
        bedrock.markConstructedNeutral();
        helper.getLevel().addFreshEntity(bedrock);

        final IronGolem vanilla = EntityType.IRON_GOLEM.create(helper.getLevel());
        helper.assertTrue(vanilla != null, "Failed to create vanilla Iron Golem");
        vanilla.moveTo(helper.absolutePos(new net.minecraft.core.BlockPos(24, 2, 4)), 0.0F, 0.0F);
        vanilla.setPlayerCreated(false);
        helper.getLevel().addFreshEntity(vanilla);

        final Player bedrockAttacker = helper.makeMockPlayer(GameType.SURVIVAL);
        bedrockAttacker.setPos(bedrock.getX() + 2.0D, bedrock.getY(), bedrock.getZ());
        final Player vanillaAttacker = helper.makeMockPlayer(GameType.SURVIVAL);
        vanillaAttacker.setPos(vanilla.getX() + 2.0D, vanilla.getY(), vanilla.getZ());

        final int[] bedrockTimestampBefore = new int[1];
        final int[] vanillaTimestampBefore = new int[1];

        helper.runAfterDelay(10, () -> {
            bedrockTimestampBefore[0] = bedrock.getLastHurtByMobTimestamp();
            vanillaTimestampBefore[0] = vanilla.getLastHurtByMobTimestamp();
            final float bedrockHealth = bedrock.getHealth();
            bedrock.hurt(helper.getLevel().damageSources().playerAttack(bedrockAttacker), 1.0F);
            vanilla.hurt(helper.getLevel().damageSources().playerAttack(vanillaAttacker), 1.0F);

            helper.assertTrue(bedrock.getHealth() == bedrockHealth,
                    "Bedrock Golem took actual damage during provocation test");
            helper.assertTrue(!bedrock.isPlayerCreated(),
                    "Bedrock Golem incorrectly entered player-created/custom-neutral semantics");
            helper.assertTrue(bedrock.getLastHurtByMob() == bedrockAttacker,
                    "Bedrock fake-hit bridge did not preserve the player as lastHurtByMob");
            helper.assertTrue(bedrock.getLastHurtByMobTimestamp() != bedrockTimestampBefore[0],
                    "Bedrock fake-hit bridge did not advance lastHurtByMobTimestamp");
            helper.assertTrue(vanilla.getLastHurtByMob() == vanillaAttacker,
                    "Vanilla control did not record its player attacker");
            helper.assertTrue(vanilla.getLastHurtByMobTimestamp() != vanillaTimestampBefore[0],
                    "Vanilla control did not advance lastHurtByMobTimestamp");

            final boolean bedrockType = bedrock.canAttackType(EntityType.PLAYER);
            final boolean vanillaType = vanilla.canAttackType(EntityType.PLAYER);
            final boolean bedrockAttack = bedrock.canAttack(bedrockAttacker);
            final boolean vanillaAttack = vanilla.canAttack(vanillaAttacker);
            helper.assertTrue(vanillaType,
                    "Vanilla natural Iron Golem baseline unexpectedly rejects EntityType.PLAYER");
            helper.assertTrue(vanillaAttack,
                    "Vanilla natural Iron Golem baseline unexpectedly rejects its survival attacker");
            helper.assertTrue(bedrockType,
                    "Bedrock canAttackType(PLAYER) is false while PlayerCreated=false");
            helper.assertTrue(bedrockAttack,
                    "Bedrock canAttack(player) is false despite natural semantics; playerCreated="
                            + bedrock.isPlayerCreated() + ", typeAllowed=" + bedrockType
                            + ", vanillaCanAttack=" + vanillaAttack);
        });

        helper.runAfterDelay(30, () -> {
            // Check the vanilla control first so a Bedrock failure cannot hide a broken
            // test baseline.
            helper.assertTrue(vanilla.getTarget() == vanillaAttacker,
                    "Vanilla Iron Golem baseline did not acquire its direct attacker");
            helper.assertTrue(bedrock.getTarget() == bedrockAttacker,
                    "Bedrock did not acquire its direct player attacker through HurtByTargetGoal; "
                            + "lastHurtMatches=" + (bedrock.getLastHurtByMob() == bedrockAttacker)
                            + ", canAttack=" + bedrock.canAttack(bedrockAttacker)
                            + ", canAttackType=" + bedrock.canAttackType(EntityType.PLAYER)
                            + ", playerCreated=" + bedrock.isPlayerCreated());

            bedrockAttacker.setPos(bedrock.getX() + 128.0D, bedrock.getY(), bedrock.getZ());
            vanillaAttacker.setPos(vanilla.getX() + 128.0D, vanilla.getY(), vanilla.getZ());
        });

        helper.runAfterDelay(150, () -> {
            helper.assertTrue(vanilla.getTarget() != vanillaAttacker,
                    "Vanilla baseline unexpectedly retained the remote player target");
            helper.assertTrue(bedrock.getTarget() != bedrockAttacker,
                    "Bedrock retained the remote player target after retaliation range ended");

            final Zombie bedrockZombie = EntityType.ZOMBIE.create(helper.getLevel());
            final Zombie vanillaZombie = EntityType.ZOMBIE.create(helper.getLevel());
            helper.assertTrue(bedrockZombie != null && vanillaZombie != null,
                    "Failed to create hostile-mob probes");
            bedrockZombie.moveTo(bedrock.getX() + 5.0D, bedrock.getY(), bedrock.getZ(), 0.0F, 0.0F);
            vanillaZombie.moveTo(vanilla.getX() + 5.0D, vanilla.getY(), vanilla.getZ(), 0.0F, 0.0F);
            helper.getLevel().addFreshEntity(bedrockZombie);
            helper.getLevel().addFreshEntity(vanillaZombie);

            helper.succeedWhen(() -> {
                helper.assertTrue(vanilla.getTarget() == vanillaZombie,
                        "Vanilla baseline has not acquired its hostile mob yet");
                helper.assertTrue(bedrock.getTarget() == bedrockZombie,
                        "Bedrock failed to reacquire a hostile mob after player retaliation ended; "
                                + "currentTarget=" + bedrock.getTarget()
                                + ", lastHurt=" + bedrock.getLastHurtByMob());
            });
        });
    }
}
''')

print('Injected diagnostic Bedrock-vs-vanilla AI GameTest harness.')
