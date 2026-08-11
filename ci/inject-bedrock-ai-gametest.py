from pathlib import Path
import json

root = Path('project')
build = root / 'build.gradle'
modjson = root / 'src/main/resources/fabric.mod.json'
testjava = root / 'src/main/java/com/mcmoddev/golems/test/BedrockNaturalAiGameTest.java'

# Preserve exact post-port/post-patch files so the test harness can be removed before
# the production build without reverting any real mod changes.
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
    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 260)
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

        final float bedrockHealth = bedrock.getHealth();
        bedrock.hurt(helper.getLevel().damageSources().playerAttack(bedrockAttacker), 1.0F);
        vanilla.hurt(helper.getLevel().damageSources().playerAttack(vanillaAttacker), 1.0F);
        helper.assertTrue(bedrock.getHealth() == bedrockHealth,
                "Bedrock Golem took actual damage during provocation test");
        helper.assertTrue(!bedrock.isPlayerCreated(),
                "Bedrock Golem incorrectly entered player-created/custom-neutral semantics");

        // Both natural-style golems should acquire their direct attacker through the same
        // HurtByTargetGoal path. Do not manually set either target in the test.
        helper.runAfterDelay(15, () -> {
            helper.assertTrue(bedrock.getTarget() == bedrockAttacker,
                    "Bedrock did not acquire its direct player attacker through HurtByTargetGoal");
            helper.assertTrue(vanilla.getTarget() == vanillaAttacker,
                    "Vanilla Iron Golem baseline did not acquire its direct attacker");

            // Teleport the attackers far beyond ordinary follow range. This reproduces the
            // user's 'successfully got it to stop being provoked' condition without death.
            bedrockAttacker.setPos(bedrock.getX() + 128.0D, bedrock.getY(), bedrock.getZ());
            vanillaAttacker.setPos(vanilla.getX() + 128.0D, vanilla.getY(), vanilla.getZ());
        });

        helper.runAfterDelay(90, () -> {
            helper.assertTrue(bedrock.getTarget() != bedrockAttacker,
                    "Bedrock retained the remote player target after retaliation range ended");
            helper.assertTrue(vanilla.getTarget() != vanillaAttacker,
                    "Vanilla baseline unexpectedly retained the remote player target");

            final Zombie bedrockZombie = EntityType.ZOMBIE.create(helper.getLevel());
            final Zombie vanillaZombie = EntityType.ZOMBIE.create(helper.getLevel());
            helper.assertTrue(bedrockZombie != null && vanillaZombie != null,
                    "Failed to create hostile-mob probes");
            bedrockZombie.moveTo(bedrock.getX() + 5.0D, bedrock.getY(), bedrock.getZ(), 0.0F, 0.0F);
            vanillaZombie.moveTo(vanilla.getX() + 5.0D, vanilla.getY(), vanilla.getZ(), 0.0F, 0.0F);
            helper.getLevel().addFreshEntity(bedrockZombie);
            helper.getLevel().addFreshEntity(vanillaZombie);

            // succeedWhen retries every tick. It catches target acquisition before either
            // golem has time to kill and clear the zombie target.
            helper.succeedWhen(() -> {
                helper.assertTrue(vanilla.getTarget() == vanillaZombie,
                        "Vanilla baseline has not acquired its hostile mob yet");
                helper.assertTrue(bedrock.getTarget() == bedrockZombie,
                        "Bedrock failed to reacquire a hostile mob after player retaliation ended");
            });
        });
    }
}
''')

print('Injected temporary Bedrock-vs-vanilla AI GameTest harness.')
