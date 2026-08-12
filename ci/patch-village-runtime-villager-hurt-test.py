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

        // This is the vanilla Villager hook invoked when a LivingEntity becomes the
        // villager's attacker. It dispatches the VILLAGER_HURT reputation event.
        extraVillager.setLastHurtByMob(extraPlayer);
        vanillaVillager.setLastHurtByMob(vanillaPlayer);
        final int extraRep = extraVillager.getPlayerReputation(extraPlayer);
        final int vanillaRep = vanillaVillager.getPlayerReputation(vanillaPlayer);
        helper.assertTrue(vanillaRep <= -100, "Vanilla villager-hurt event did not cross hostility threshold; rep=" + vanillaRep);
        helper.assertTrue(extraRep == vanillaRep, "Extra-side villager reputation differs from vanilla; extra=" + extraRep + ", vanilla=" + vanillaRep);

        tickUntilPlayerTarget(extra, extraPlayer);
        tickUntilPlayerTarget(vanilla, vanillaPlayer);
        final boolean extraTargeted = extra.getTarget() == extraPlayer;
        final boolean vanillaTargeted = vanilla.getTarget() == vanillaPlayer;

        cleanupPlayer(helper, extraPlayer); cleanupPlayer(helper, vanillaPlayer);
        extraVillager.discard(); vanillaVillager.discard(); vanilla.discard(); extra.discard();
        helper.assertTrue(vanillaTargeted, "Vanilla natural Iron Golem ignored villager-hurt player");
        helper.assertTrue(extraTargeted, "Real T-built Extra Golem ignored villager-hurt player");
        helper.succeed();
    }

'''
s = s.replace(marker, method + marker, 1)
p.write_text(s)
print('Added real villager-hurt -> reputation -> runtime target parity test.')
