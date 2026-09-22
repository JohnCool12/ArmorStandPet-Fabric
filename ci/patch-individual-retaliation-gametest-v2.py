from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/test/IndividualRetaliationGameTest.java')
s = p.read_text()

def replace_method(name, replacement):
    global s
    sig = f'    public void {name}('
    start = s.find(sig)
    if start < 0:
        raise SystemExit(f'Missing {name}')
    anno = s.rfind('    @GameTest', 0, start)
    if anno < 0:
        raise SystemExit(f'Missing annotation for {name}')
    brace = s.find('{', start)
    depth = 0
    end = None
    for i in range(brace, len(s)):
        if s[i] == '{': depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise SystemExit(f'Unclosed {name}')
    s = s[:anno] + replacement + s[end:]

replace_method('directPunchDoesNotAlertBystanderExtraGolem', r'''    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 100)
    public void directPunchDoesNotAlertBystanderExtraGolem(final GameTestHelper helper) {
        final GolemBase hit = construct(helper, Blocks.OBSIDIAN, new BlockPos(6, 20, 6));
        final GolemBase bystander = construct(helper, Blocks.DIAMOND_BLOCK, new BlockPos(18, 20, 6));
        final ServerPlayer p = player(helper, "ExtraPuncher");
        p.setPos(hit.getX() + 3.0D, hit.getY(), hit.getZ());
        hit.hurt(p.damageSources().playerAttack(p), 1.0F);

        // The real damage path must record the attacker only on the struck golem.
        final boolean localStimulus = hit.getLastHurtByMob() == p;
        final boolean bystanderHasNoStimulus = bystander.getLastHurtByMob() == null
                && bystander.getPersistentAngerTarget() == null
                && bystander.getRemainingPersistentAngerTime() == 0
                && bystander.getTarget() == null;

        // Simulate any unknown behavior/integration attempting to copy the struck
        // golem's player target onto the bystander. The production provenance guard
        // must reject it because this bystander has no local reason to hate the player.
        bystander.setTarget(p);
        final boolean copiedTargetRejected = bystander.getTarget() == null;

        // Conversely, a direct local provocation must remain sufficient to allow the
        // target assignment used by HurtByTargetGoal.
        hit.setLastHurtByMob(p);
        hit.setTarget(p);
        final boolean directTargetAllowed = hit.getTarget() == p;
        final String hitState = state(hit), bystanderState = state(bystander);

        cleanup(helper, p, hit, bystander);
        helper.assertTrue(localStimulus, "Struck Extra Golem did not retain its own attacker: " + hitState);
        helper.assertTrue(bystanderHasNoStimulus, "Punch propagated attacker/anger state to unpunched Extra Golem: " + bystanderState);
        helper.assertTrue(copiedTargetRejected, "Unpunched different-material Extra Golem accepted an unprovenanced copied player target: " + bystanderState);
        helper.assertTrue(directTargetAllowed, "Directly provoked Extra Golem was blocked from targeting its attacker: " + hitState);
        helper.succeed();
    }''')

replace_method('vanillaNaturalIronGolemDirectPunchIsIndividual', r'''    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 100)
    public void vanillaNaturalIronGolemDirectPunchIsIndividual(final GameTestHelper helper) {
        final BlockPos base = helper.absolutePos(new BlockPos(6,20,24));
        final IronGolem hit = vanilla(helper, base.getX(), base.getY(), base.getZ());
        final IronGolem bystander = vanilla(helper, hit.getX() + 12.0D, hit.getY(), hit.getZ());
        final ServerPlayer p = player(helper, "VanillaPuncher");
        p.setPos(hit.getX() + 3.0D, hit.getY(), hit.getZ());
        hit.hurt(p.damageSources().playerAttack(p), 1.0F);
        final boolean localStimulus = hit.getLastHurtByMob() == p;
        final boolean bystanderStayedUnprovoked = bystander.getLastHurtByMob() == null
                && bystander.getPersistentAngerTarget() == null
                && bystander.getRemainingPersistentAngerTime() == 0
                && bystander.getTarget() == null;
        final String hitState = state(hit), bystanderState = state(bystander);
        cleanup(helper, p, hit, bystander);
        helper.assertTrue(localStimulus, "Vanilla struck Iron Golem did not retain its own attacker: " + hitState);
        helper.assertTrue(bystanderStayedUnprovoked, "Vanilla punch propagated retaliation state to nearby Iron Golem: " + bystanderState);
        helper.succeed();
    }''')

p.write_text(s)
print('Refined retaliation tests to verify local attack provenance and village exception.')
