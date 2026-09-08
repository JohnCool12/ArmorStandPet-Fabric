from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/test/VillageReputationGameTest.java')
text = p.read_text()
old = '''        extraPlayer.setGameMode(GameType.SURVIVAL);
        vanillaPlayer.setGameMode(GameType.SURVIVAL);
'''
new = '''        // The GameTest helper creates synthetic ServerPlayers whose convenience
        // setGameMode call can leave the underlying interaction manager/abilities in
        // creative state. Drive the same server game-mode controller directly and
        // normalize the abilities so Player.isCreative() is genuinely false.
        extraPlayer.gameMode.changeGameModeForPlayer(GameType.SURVIVAL);
        vanillaPlayer.gameMode.changeGameModeForPlayer(GameType.SURVIVAL);
        extraPlayer.getAbilities().invulnerable = false;
        extraPlayer.getAbilities().instabuild = false;
        extraPlayer.getAbilities().mayfly = false;
        extraPlayer.getAbilities().flying = false;
        vanillaPlayer.getAbilities().invulnerable = false;
        vanillaPlayer.getAbilities().instabuild = false;
        vanillaPlayer.getAbilities().mayfly = false;
        vanillaPlayer.getAbilities().flying = false;
        extraPlayer.onUpdateAbilities();
        vanillaPlayer.onUpdateAbilities();
'''
if text.count(old) != 1:
    raise SystemExit(f'Expected one synthetic-player game-mode block, found {text.count(old)}')
text = text.replace(old, new, 1)

old_assert = '''        helper.assertTrue(!extraPlayer.isCreative() && !vanillaPlayer.isCreative(),
                "Server-player controls are still Creative and therefore invalid village-defense targets");
'''
new_assert = '''        helper.assertTrue(extraPlayer.gameMode.getGameModeForPlayer() == GameType.SURVIVAL
                        && vanillaPlayer.gameMode.getGameModeForPlayer() == GameType.SURVIVAL,
                "Server-player interaction managers are not actually in Survival mode");
        helper.assertTrue(!extraPlayer.isCreative() && !vanillaPlayer.isCreative(),
                "Server-player controls are still Creative and therefore invalid village-defense targets");
'''
if text.count(old_assert) != 1:
    raise SystemExit(f'Expected one creative-state assertion, found {text.count(old_assert)}')
text = text.replace(old_assert, new_assert, 1)
p.write_text(text)
print('Forced registered GameTest ServerPlayers into true Survival state.')
