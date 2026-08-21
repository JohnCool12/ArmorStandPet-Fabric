from pathlib import Path
import json


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count}: {old[:120]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# V8 valid-respawn path: do not emit any presentation at the death location.
# Teleport first, then queue the destination-side chorus teleport sound/particles.
replace_once(
    "common/src/main/java/artifacts/component/ability/DeathProtectionTeleport.java",
    "package artifacts.component.ability;\n\n",
    "package artifacts.component.ability;\n\nimport artifacts.compat.hardcorerevival.ChorusTotemRespawnEffects;\n",
)

replace_once(
    "common/src/main/java/artifacts/component/ability/DeathProtectionTeleport.java",
    """                ServerLevel oldLevel = level;\n                player.teleportTo(respawn.newLevel(), respawn.pos().x, respawn.pos().y, respawn.pos().z, respawn.yRot(), respawn.xRot());\n                oldLevel.playSound(null, oldX, oldY, oldZ, SoundEvents.CHORUS_FRUIT_TELEPORT, SoundSource.PLAYERS, 1, 1);\n                player.serverLevel().playSound(null, player.getX(), player.getY(), player.getZ(), SoundEvents.CHORUS_FRUIT_TELEPORT, SoundSource.PLAYERS, 1, 1);\n                return;\n""",
    """                player.teleportTo(respawn.newLevel(), respawn.pos().x, respawn.pos().y, respawn.pos().z, respawn.yRot(), respawn.xRot());\n                ChorusTotemRespawnEffects.scheduleTeleportEffects(player);\n                return;\n""",
)

# V8 Hardcore Revival post-save presentation used server.execute(), which may execute
# immediately when already on the server thread. Queue the activation presentation
# instead; the player-tick hook below will only release it on a later server tick.
replace_once(
    "common/src/main/java/artifacts/compat/hardcorerevival/HardcoreRevivalFinalDeathCompat.java",
    """    public static void schedulePostTeleportEffects(ServerPlayer player) {\n        player.server.execute(() -> {\n            ServerPlayer live = player.server.getPlayerList().getPlayer(player.getUUID());\n            if (live == null || !live.isAlive()) {\n                return;\n            }\n            live.serverLevel().playSound(null, live.getX(), live.getY(), live.getZ(),\n                    SoundEvents.TOTEM_USE, SoundSource.PLAYERS, 1F, 1F);\n            NetworkHandler.sendToPlayer(live, new ChorusTotemUsedPacket());\n        });\n    }\n""",
    """    public static void schedulePostTeleportEffects(ServerPlayer player) {\n        ChorusTotemRespawnEffects.scheduleActivationEffects(player);\n    }\n""",
)

# Cross-loader, Mojmap-compatible one-tick queue. The due tick is recorded explicitly,
# so even if the save is scheduled before the player's tick phase, effects cannot be
# emitted during the same server tick as teleportTo(). Weak keys avoid retaining a
# disconnected player if they vanish before the next tick.
compat_dir = Path("common/src/main/java/artifacts/compat/hardcorerevival")
(compat_dir / "ChorusTotemRespawnEffects.java").write_text(r'''package artifacts.compat.hardcorerevival;

import artifacts.network.ChorusTotemUsedPacket;
import artifacts.network.NetworkHandler;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;

import java.util.Map;
import java.util.WeakHashMap;

public final class ChorusTotemRespawnEffects {
    private static final Map<ServerPlayer, Pending> PENDING = new WeakHashMap<>();

    private ChorusTotemRespawnEffects() {
    }

    public static void scheduleTeleportEffects(ServerPlayer player) {
        schedule(player, true, false);
    }

    public static void scheduleActivationEffects(ServerPlayer player) {
        schedule(player, false, true);
    }

    private static void schedule(ServerPlayer player, boolean teleportEffects, boolean activationEffects) {
        int dueTick = player.server.getTickCount() + 1;
        Pending previous = PENDING.get(player);
        if (previous != null) {
            dueTick = Math.max(dueTick, previous.dueTick());
            teleportEffects |= previous.teleportEffects();
            activationEffects |= previous.activationEffects();
        }
        PENDING.put(player, new Pending(dueTick, teleportEffects, activationEffects));
    }

    public static void tick(ServerPlayer player) {
        Pending pending = PENDING.get(player);
        if (pending == null || player.server.getTickCount() < pending.dueTick()) {
            return;
        }
        PENDING.remove(player);

        if (!player.isAlive()) {
            return;
        }

        ServerLevel destinationLevel = player.serverLevel();
        double x = player.getX();
        double y = player.getY();
        double z = player.getZ();

        if (pending.teleportEffects()) {
            destinationLevel.playSound(null, x, y, z,
                    SoundEvents.CHORUS_FRUIT_TELEPORT, SoundSource.PLAYERS, 1F, 1F);
            destinationLevel.broadcastEntityEvent(player, (byte) 46);
        }

        if (pending.activationEffects()) {
            // The custom packet supplies the owner's local TOTEM_USE sound plus the
            // item-activation animation. Exclude that owner from the server-side copy
            // so the local sound is not doubled; other nearby players still hear it.
            destinationLevel.playSound(player, x, y, z,
                    SoundEvents.TOTEM_USE, SoundSource.PLAYERS, 1F, 1F);
            NetworkHandler.sendToPlayer(player, new ChorusTotemUsedPacket());
        }
    }

    private record Pending(int dueTick, boolean teleportEffects, boolean activationEffects) {
    }
}
''', encoding="utf-8")

mixin_dir = Path("common/src/main/java/artifacts/mixin/compat/hardcorerevival")
(mixin_dir / "ServerPlayerRespawnEffectsMixin.java").write_text(r'''package artifacts.mixin.compat.hardcorerevival;

import artifacts.compat.hardcorerevival.ChorusTotemRespawnEffects;
import net.minecraft.server.level.ServerPlayer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ServerPlayer.class)
public abstract class ServerPlayerRespawnEffectsMixin {
    @Inject(method = "tick", at = @At("HEAD"))
    private void artifacts$runQueuedChorusTotemRespawnEffects(CallbackInfo ci) {
        ChorusTotemRespawnEffects.tick((ServerPlayer) (Object) this);
    }
}
''', encoding="utf-8")

mixins = Path("common/src/main/resources/mixins.artifacts.common.json")
data = json.loads(mixins.read_text(encoding="utf-8"))
name = "compat.hardcorerevival.ServerPlayerRespawnEffectsMixin"
if name not in data["mixins"]:
    data["mixins"].append(name)
mixins.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
