from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/test/VillageRuntimeParityGameTest.java')
s = p.read_text()
marker = '''    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 80)\n    public void legacyPlayerCreatedGolemMigratesOnLoadAndUsesRuntimeReputation(final GameTestHelper helper) {\n'''
if s.count(marker) != 1:
    raise SystemExit('Legacy test marker missing')
method = r'''    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 80)
    public void villagerHurtEventMakesRealTConstructedGolemHostileLikeVanilla(final GameTestHelper helper) {
        final GolemBase extra = constructFromT(helper, Blocks.OBSIDIAN, new BlockPos(6, 20, 6));
        helper.assertTrue(!extra.isPlayerCreated(), "Fresh T-built Extra Golem is still player-created");
        final IronGolem vanilla = addNaturalVanillaControl(helper, extra.getX() + 40.0D, extra.getY(), extra.getZ());
        final Villager extraVillager = addVillager(helper, extra.getX(), extra.getY(), extra.getZ() + 1.0D);
        final Villager vanillaVillager = addVillager(helper, vanilla.getX(), vanilla.getY(), vanilla.getZ() + 1.0D);
        final ServerPlayer extraPlayer = makeListedSurvivalPlayer(helper, "ExtraVillagerHurter");
        final ServerPlayer vanillaPlayer = makeListedSurvivalPlayer(helper, "VanillaVillagerHurter");
        extraPlayer.setPos(extra.getX() + 7.0D, extra.getY(), extra.getZ());
        vanillaPlayer.setPos(vanilla.getX() + 7.0D, vanilla.getY(), vanilla.getZ());

        // One vanilla VILLAGER_HURT event adds 25 MINOR_NEGATIVE gossip. First prove
        // that Extra and vanilla receive exactly the same reputation and targeting
        // result below the -100 DefendVillageTargetGoal threshold.
        extraVillager.setLastHurtByMob(extraPlayer);
        vanillaVillager.setLastHurtByMob(vanillaPlayer);
        final int extraRepAfterOne = extraVillager.getPlayerReputation(extraPlayer);
        final int vanillaRepAfterOne = vanillaVillager.getPlayerReputation(vanillaPlayer);
        helper.assertTrue(extraRepAfterOne == vanillaRepAfterOne,
                "One-hit reputation differs; extra=" + extraRepAfterOne + ", vanilla=" + vanillaRepAfterOne);
        helper.assertTrue(vanillaRepAfterOne == -25,
                "Unexpected vanilla 1.21.1 one-hit reputation; got " + vanillaRepAfterOne);

        tickUntilPlayerTarget(extra, extraPlayer);
        tickUntilPlayerTarget(vanilla, vanillaPlayer);
        final boolean extraAfterOne = extra.getTarget() == extraPlayer;
        final boolean vanillaAfterOne = vanilla.getTarget() == vanillaPlayer;
        helper.assertTrue(extraAfterOne == vanillaAfterOne,
                "One-hit target behavior differs; extra=" + extraAfterOne + ", vanilla=" + vanillaAfterOne);

        // Clear any transient target, then add three more identical vanilla hurt
        // events. Four total MINOR_NEGATIVE(25) events reach reputation -100, which
        // is exactly the vanilla DefendVillageTargetGoal hostility threshold.
        extra.setTarget(null);
        vanilla.setTarget(null);
        for (int i = 0; i < 3; i++) {
            extraVillager.setLastHurtByMob(extraPlayer);
            vanillaVillager.setLastHurtByMob(vanillaPlayer);
        }
        final int extraRepAtThreshold = extraVillager.getPlayerReputation(extraPlayer);
        final int vanillaRepAtThreshold = vanillaVillager.getPlayerReputation(vanillaPlayer);
        helper.assertTrue(extraRepAtThreshold == vanillaRepAtThreshold,
                "Threshold reputation differs; extra=" + extraRepAtThreshold + ", vanilla=" + vanillaRepAtThreshold);
        helper.assertTrue(vanillaRepAtThreshold <= -100,
                "Repeated vanilla villager-hurt events failed to reach hostility threshold; rep=" + vanillaRepAtThreshold);

        tickUntilPlayerTarget(extra, extraPlayer);
        tickUntilPlayerTarget(vanilla, vanillaPlayer);
        final boolean extraAtThreshold = extra.getTarget() == extraPlayer;
        final boolean vanillaAtThreshold = vanilla.getTarget() == vanillaPlayer;

        cleanupPlayer(helper, extraPlayer); cleanupPlayer(helper, vanillaPlayer);
        extraVillager.discard(); vanillaVillager.discard(); vanilla.discard(); extra.discard();
        helper.assertTrue(vanillaAtThreshold,
                "Vanilla natural Iron Golem did not target player after villager-hurt reputation crossed threshold");
        helper.assertTrue(extraAtThreshold,
                "Real T-built Extra Golem did not target player after identical villager-hurt reputation crossed threshold");
        helper.succeed();
    }

'''
s = s.replace(marker, method + marker, 1)
p.write_text(s)
print('Added one-hit and repeated-hurt vanilla-vs-Extra runtime reputation parity test.')
