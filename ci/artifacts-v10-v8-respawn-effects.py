from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count}: {old[:120]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# V8 valid-respawn path: do not emit any presentation back at the death location.
# Wait one full server tick after teleportTo, then play the chorus teleport sound and
# exact vanilla teleport particle entity-event around the live player at the resolved
# respawn destination.
replace_once(
    "common/src/main/java/artifacts/component/ability/DeathProtectionTeleport.java",
    "import net.minecraft.server.level.ServerLevel;\nimport net.minecraft.server.level.ServerPlayer;\n",
    "import net.minecraft.server.TickTask;\nimport net.minecraft.server.level.ServerLevel;\nimport net.minecraft.server.level.ServerPlayer;\n",
)

replace_once(
    "common/src/main/java/artifacts/component/ability/DeathProtectionTeleport.java",
    """                ServerLevel oldLevel = level;\n                player.teleportTo(respawn.newLevel(), respawn.pos().x, respawn.pos().y, respawn.pos().z, respawn.yRot(), respawn.xRot());\n                oldLevel.playSound(null, oldX, oldY, oldZ, SoundEvents.CHORUS_FRUIT_TELEPORT, SoundSource.PLAYERS, 1, 1);\n                player.serverLevel().playSound(null, player.getX(), player.getY(), player.getZ(), SoundEvents.CHORUS_FRUIT_TELEPORT, SoundSource.PLAYERS, 1, 1);\n                return;\n""",
    """                player.teleportTo(respawn.newLevel(), respawn.pos().x, respawn.pos().y, respawn.pos().z, respawn.yRot(), respawn.xRot());\n                player.server.schedule(new TickTask(player.server.getTickCount() + 1, () -> {\n                    ServerPlayer live = player.server.getPlayerList().getPlayer(player.getUUID());\n                    if (live == null || !live.isAlive()) {\n                        return;\n                    }\n\n                    ServerLevel destinationLevel = live.serverLevel();\n                    destinationLevel.playSound(null, live.getX(), live.getY(), live.getZ(),\n                            SoundEvents.CHORUS_FRUIT_TELEPORT, SoundSource.PLAYERS, 1, 1);\n                    destinationLevel.broadcastEntityEvent(live, (byte) 46);\n                }));\n                return;\n""",
)

# V8 Hardcore Revival post-save presentation: server.execute() can run immediately
# on the server thread. Schedule for the next server tick instead so the client has
# processed/rendered the respawn teleport first. Keep the owner's local TOTEM_USE
# sound in the custom packet and exclude that owner from the server-side copy, exactly
# like Artifacts' ordinary death-protection path, preventing a doubled local sound.
replace_once(
    "common/src/main/java/artifacts/compat/hardcorerevival/HardcoreRevivalFinalDeathCompat.java",
    "import net.minecraft.server.level.ServerPlayer;\n",
    "import net.minecraft.server.TickTask;\nimport net.minecraft.server.level.ServerPlayer;\n",
)

replace_once(
    "common/src/main/java/artifacts/compat/hardcorerevival/HardcoreRevivalFinalDeathCompat.java",
    """    public static void schedulePostTeleportEffects(ServerPlayer player) {\n        player.server.execute(() -> {\n            ServerPlayer live = player.server.getPlayerList().getPlayer(player.getUUID());\n            if (live == null || !live.isAlive()) {\n                return;\n            }\n            live.serverLevel().playSound(null, live.getX(), live.getY(), live.getZ(),\n                    SoundEvents.TOTEM_USE, SoundSource.PLAYERS, 1F, 1F);\n            NetworkHandler.sendToPlayer(live, new ChorusTotemUsedPacket());\n        });\n    }\n""",
    """    public static void schedulePostTeleportEffects(ServerPlayer player) {\n        player.server.schedule(new TickTask(player.server.getTickCount() + 1, () -> {\n            ServerPlayer live = player.server.getPlayerList().getPlayer(player.getUUID());\n            if (live == null || !live.isAlive()) {\n                return;\n            }\n            live.serverLevel().playSound(live, live.getX(), live.getY(), live.getZ(),\n                    SoundEvents.TOTEM_USE, SoundSource.PLAYERS, 1F, 1F);\n            NetworkHandler.sendToPlayer(live, new ChorusTotemUsedPacket());\n        }));\n    }\n""",
)
