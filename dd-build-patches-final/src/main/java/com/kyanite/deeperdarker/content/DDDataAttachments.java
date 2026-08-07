package com.kyanite.deeperdarker.content;

import com.kyanite.deeperdarker.DeeperDarker;
import com.kyanite.deeperdarker.content.data.PlayerData;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.minecraft.world.entity.player.Player;

/**
 * Fabric-native replacement for NeoForge's transient PLAYER_DATA attachment.
 * The original attachment had no persistence codec and no copy-on-death behavior,
 * so createDefaulted gives the closest lifecycle semantics on Fabric.
 */
public final class DDDataAttachments {
    public static final AttachmentType<PlayerData> PLAYER_DATA = AttachmentRegistry.createDefaulted(
            DeeperDarker.rl("player_data"), PlayerData::new);

    private DDDataAttachments() {}

    public static PlayerData get(Player player) {
        return player.getAttachedOrCreate(PLAYER_DATA);
    }

    public static void clear(Player player) {
        player.removeAttached(PLAYER_DATA);
    }
}
