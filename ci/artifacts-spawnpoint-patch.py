from pathlib import Path

p = Path('common/src/main/java/artifacts/component/ability/DeathProtectionTeleport.java')
s = p.read_text(encoding='utf-8')

s = s.replace(
    'import net.minecraft.server.level.ServerLevel;\n',
    'import net.minecraft.server.level.ServerLevel;\nimport net.minecraft.server.level.ServerPlayer;\n'
)
s = s.replace(
    'import net.minecraft.world.level.gameevent.GameEvent;\n',
    'import net.minecraft.world.level.gameevent.GameEvent;\nimport net.minecraft.world.level.portal.DimensionTransition;\n'
)

old = '''    public static void teleport(LivingEntity entity, ServerLevel level) {\n        double oldX = entity.getX();\n        double oldY = entity.getY();\n        double oldZ = entity.getZ();\n\n        for (int i = 0; i < 32; ++i) {\n'''
new = '''    public static void teleport(LivingEntity entity, ServerLevel level) {\n        double oldX = entity.getX();\n        double oldY = entity.getY();\n        double oldZ = entity.getZ();\n\n        // Players with a valid personal respawn point are sent to that spawn rather than a random location.\n        // Deliberately do not fall back to the global world spawn: if the personal spawn is absent/invalid,\n        // preserve the original Chorus Totem random-teleport behavior below.\n        if (entity instanceof ServerPlayer player && player.getRespawnPosition() != null) {\n            DimensionTransition respawn = player.findRespawnPositionAndUseSpawnBlock(false, DimensionTransition.DO_NOTHING);\n            if (!respawn.missingRespawnBlock()) {\n                if (player.isPassenger()) {\n                    player.stopRiding();\n                }\n\n                ServerLevel oldLevel = level;\n                player.teleportTo(respawn.newLevel(), respawn.pos().x, respawn.pos().y, respawn.pos().z, respawn.yRot(), respawn.xRot());\n                oldLevel.playSound(null, oldX, oldY, oldZ, SoundEvents.CHORUS_FRUIT_TELEPORT, SoundSource.PLAYERS, 1, 1);\n                player.serverLevel().playSound(null, player.getX(), player.getY(), player.getZ(), SoundEvents.CHORUS_FRUIT_TELEPORT, SoundSource.PLAYERS, 1, 1);\n                return;\n            }\n        }\n\n        for (int i = 0; i < 32; ++i) {\n'''
if s.count(old) != 1:
    raise SystemExit(f'expected exactly one teleport method prefix, found {s.count(old)}')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
