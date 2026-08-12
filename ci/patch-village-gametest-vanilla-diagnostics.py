from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/test/VillageReputationGameTest.java')
text = p.read_text()

text = text.replace(
    'import net.minecraft.world.entity.ai.gossip.GossipType;\n',
    'import net.minecraft.world.entity.ai.gossip.GossipType;\n'
    'import net.minecraft.world.entity.ai.goal.target.DefendVillageTargetGoal;\n'
    'import net.minecraft.world.entity.ai.targeting.TargetingConditions;\n'
)
text = text.replace(
    'import net.minecraft.world.entity.npc.Villager;\n',
    'import net.minecraft.world.entity.npc.Villager;\n'
    'import net.minecraft.world.entity.player.Player;\n'
    'import net.minecraft.world.phys.AABB;\n'
)
text = text.replace('import java.util.UUID;\n', 'import java.util.List;\nimport java.util.UUID;\n')

old = '''        helper.runAfterDelay(180L, () -> {
            final boolean vanillaOk = vanilla.getTarget() == vanillaPlayer;
            final boolean extraOk = extra.getTarget() == extraPlayer;
            final String vanillaTarget = String.valueOf(vanilla.getTarget());
            final String extraTarget = String.valueOf(extra.getTarget());
            removeHeadlessPlayers(helper, extraPlayer, vanillaPlayer);

            helper.assertTrue(vanillaOk,
                    "Vanilla natural Iron Golem did not target the very-low-reputation player after 180 ticks; target=" + vanillaTarget);
            helper.assertTrue(extraOk,
                    "T-built Extra Golem did not match vanilla low-reputation hostility after 180 ticks; target=" + extraTarget);
            helper.succeed();
        });'''

new = '''        helper.runAfterDelay(180L, () -> {
            final boolean vanillaOk = vanilla.getTarget() == vanillaPlayer;
            final boolean extraOk = extra.getTarget() == extraPlayer;
            final String vanillaTarget = String.valueOf(vanilla.getTarget());
            final String extraTarget = String.valueOf(extra.getTarget());

            // Mirror DefendVillageTargetGoal.canUse() exactly so a failed vanilla
            // control tells us which headless-GameTest prerequisite is absent.
            final TargetingConditions conditions = TargetingConditions.forCombat().range(64.0D);
            final AABB vanillaBox = vanilla.getBoundingBox().inflate(10.0D, 8.0D, 10.0D);
            final AABB extraBox = extra.getBoundingBox().inflate(10.0D, 8.0D, 10.0D);
            final List<Villager> vanillaVillagers = helper.getLevel().getNearbyEntities(
                    Villager.class, conditions, vanilla, vanillaBox);
            final List<Player> vanillaPlayers = helper.getLevel().getNearbyPlayers(
                    conditions, vanilla, vanillaBox);
            final List<Villager> extraVillagers = helper.getLevel().getNearbyEntities(
                    Villager.class, conditions, extra, extraBox);
            final List<Player> extraPlayers = helper.getLevel().getNearbyPlayers(
                    conditions, extra, extraBox);
            final boolean vanillaGoalCanUse = new DefendVillageTargetGoal(vanilla).canUse();
            final boolean extraGoalCanUse = new DefendVillageTargetGoal(extra).canUse();
            final int vanillaRep = vanillaVillager.getPlayerReputation(vanillaPlayer);
            final int extraRep = extraVillager.getPlayerReputation(extraPlayer);
            final String vanillaDiag = "target=" + vanillaTarget
                    + ", directCanUse=" + vanillaGoalCanUse
                    + ", nearbyVillagers=" + vanillaVillagers.size()
                    + ", expectedVillagerPresent=" + vanillaVillagers.contains(vanillaVillager)
                    + ", nearbyPlayers=" + vanillaPlayers.size()
                    + ", expectedPlayerPresent=" + vanillaPlayers.contains(vanillaPlayer)
                    + ", reputation=" + vanillaRep
                    + ", playerCreated=" + vanilla.isPlayerCreated()
                    + ", playerCreative=" + vanillaPlayer.isCreative()
                    + ", playerSpectator=" + vanillaPlayer.isSpectator()
                    + ", playerAlive=" + vanillaPlayer.isAlive();
            final String extraDiag = "target=" + extraTarget
                    + ", directCanUse=" + extraGoalCanUse
                    + ", nearbyVillagers=" + extraVillagers.size()
                    + ", expectedVillagerPresent=" + extraVillagers.contains(extraVillager)
                    + ", nearbyPlayers=" + extraPlayers.size()
                    + ", expectedPlayerPresent=" + extraPlayers.contains(extraPlayer)
                    + ", reputation=" + extraRep
                    + ", playerCreated=" + extra.isPlayerCreated()
                    + ", playerCreative=" + extraPlayer.isCreative()
                    + ", playerSpectator=" + extraPlayer.isSpectator()
                    + ", playerAlive=" + extraPlayer.isAlive();

            removeHeadlessPlayers(helper, extraPlayer, vanillaPlayer);

            helper.assertTrue(vanillaOk,
                    "Vanilla natural Iron Golem did not target the very-low-reputation player after 180 ticks; " + vanillaDiag);
            helper.assertTrue(extraOk,
                    "T-built Extra Golem did not match vanilla low-reputation hostility after 180 ticks; " + extraDiag);
            helper.succeed();
        });'''

if text.count(old) != 1:
    raise SystemExit(f'Expected one timed village assertion block, found {text.count(old)}')
text = text.replace(old, new, 1)
p.write_text(text)
print('Instrumented village reputation GameTest with exact vanilla DefendVillageTargetGoal prerequisites.')
