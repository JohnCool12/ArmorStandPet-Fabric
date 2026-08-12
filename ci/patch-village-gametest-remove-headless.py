from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/test/VillageReputationGameTest.java')
text = p.read_text()
old = '''            helper.assertTrue(extra.getTarget() == extraPlayer,
                    "T-built Extra Golem failed vanilla village-reputation hostility; target=" + extra.getTarget());
        });'''
new = '''            helper.assertTrue(extra.getTarget() == extraPlayer,
                    "T-built Extra Golem failed vanilla village-reputation hostility; target=" + extra.getTarget());

            // Both assertions have now passed. Remove the intentionally connectionless
            // AI-only players before GameTest's ReportGameListener broadcasts its pass
            // message to every level player.
            helper.getLevel().players().remove(extraPlayer);
            helper.getLevel().players().remove(vanillaPlayer);
        });'''
if text.count(old) != 1:
    raise SystemExit(f'Expected one GameTest success block, found {text.count(old)}')
p.write_text(text.replace(old, new, 1))
print('Patched village reputation GameTest to remove headless players before pass reporting.')
