package cofh.ensorcellation.fabric.runtime;

import cofh.core.fabric.util.AreaEffectHelper;
import cofh.ensorcellation.fabric.enchantment.EnsorEnchantments;
import net.fabricmc.fabric.api.event.player.AttackBlockCallback;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.ActionResult;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/** Fabric counterpart of CoFH AreaEffectEvents for Air Affinity and Excavating. */
public final class MiningRuntime {
    private record PendingBreak(BlockPos origin, List<BlockPos> area) {}

    private static final Map<UUID, Direction> LAST_FACE = new ConcurrentHashMap<>();
    private static final Map<UUID, PendingBreak> PENDING = new ConcurrentHashMap<>();
    private static final ThreadLocal<Boolean> AREA_BREAK = ThreadLocal.withInitial(() -> false);

    public static void register() {
        AttackBlockCallback.EVENT.register((player, world, hand, pos, direction) -> {
            LAST_FACE.put(player.getUUID(), direction);
            return ActionResult.PASS;
        });
        PlayerBlockBreakEvents.BEFORE.register((world, player, pos, state, blockEntity) -> {
            if (AREA_BREAK.get()) return true;
            PENDING.remove(player.getUUID());
            int level = EnsorEnchantments.level(player.getMainHandItem(), world, "excavating");
            Direction face = LAST_FACE.get(player.getUUID());
            if (level > 0 && face != null && !player.isSecondaryUseActive()) {
                List<BlockPos> area = AreaEffectHelper.getBreakableBlocks(world, pos, face, player.getMainHandItem(), level);
                if (!area.isEmpty()) PENDING.put(player.getUUID(), new PendingBreak(pos.immutable(), List.copyOf(area)));
            }
            return true;
        });
        PlayerBlockBreakEvents.AFTER.register((world, player, pos, state, blockEntity) -> {
            if (AREA_BREAK.get() || !(player instanceof ServerPlayer serverPlayer)) return;
            PendingBreak pending = PENDING.remove(player.getUUID());
            if (pending == null || !pending.origin().equals(pos) || pending.area().isEmpty()) return;
            AREA_BREAK.set(true);
            try {
                for (BlockPos extra : pending.area()) {
                    if (serverPlayer.getMainHandItem().isEmpty()) break;
                    serverPlayer.gameMode.destroyBlock(extra);
                }
            } finally {
                AREA_BREAK.set(false);
            }
        });
    }

    public static float modifyDestroyProgress(float original, Player player, BlockGetter getter, BlockPos pos) {
        float result = original;
        ItemStack tool = player.getMainHandItem();
        // Air Affinity is a head-armor enchantment in the original mod, so use the
        // equipped enchantment level rather than looking at the mining tool.
        int airAffinity = EnsorEnchantments.equipped(player, "air_affinity");
        if (airAffinity > 0 && !player.onGround()) result *= 5.0F;

        int excavating = EnsorEnchantments.level(tool, player.level(), "excavating");
        Direction face = LAST_FACE.get(player.getUUID());
        if (excavating <= 0 || face == null || player.isSecondaryUseActive() || !(getter instanceof Level level)) return result;
        List<BlockPos> area = AreaEffectHelper.getBreakableBlocks(level, pos, face, tool, excavating);
        if (area.size() <= 1) return result;

        float areaMod = Mth.clamp(1.0F - 0.01F * area.size(), 0.1F, 1.0F);
        float initialHardness = level.getBlockState(pos).getDestroySpeed(level, pos);
        float maxHardness = initialHardness;
        for (BlockPos extra : area) maxHardness = Math.max(maxHardness, level.getBlockState(extra).getDestroySpeed(level, extra));
        if (maxHardness > initialHardness && initialHardness >= 0.0F) areaMod *= initialHardness / maxHardness;
        return result * areaMod;
    }

    private MiningRuntime() {}
}
