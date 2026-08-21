from pathlib import Path

path = Path('common/src/main/java/artifacts/component/ability/DeathProtectionTeleport.java')
text = path.read_text(encoding='utf-8')
old = '                player.teleportTo(respawn.newLevel(), respawn.pos().x, respawn.pos().y, respawn.pos().z, respawn.yRot(), respawn.xRot());\n'
new = old + '                player.serverLevel().broadcastEntityEvent(player, (byte) 46);\n'
count = text.count(old)
if count != 1:
    raise SystemExit(f'Expected exactly one direct respawn teleport call, found {count}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
